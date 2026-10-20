"""Synthetic-only optional TensorFlow tests. No fit or optimizer updates."""
import importlib.util
from unittest.mock import patch

import numpy as np
import pytest

from skin_analyzer.image_io import preprocess_image
from skin_analyzer.model import build_model
from skin_analyzer.model_contract import SKIN_TYPE_CLASSES

requires_tf = pytest.mark.skipif(
    importlib.util.find_spec("tensorflow") is None,
    reason="TensorFlow is not installed; optional runtime and serialization unverified",
)


def test_pretrained_weights_are_blocked_even_without_tensorflow():
    with pytest.raises(ValueError, match="pretrained weights are disabled"):
        build_model(weights="imagenet")


@pytest.fixture(scope="module")
def tf():
    import tensorflow
    return tensorflow


@pytest.fixture(scope="module")
def model(tf):
    with patch.object(tf.keras.applications, "ResNet50", wraps=tf.keras.applications.ResNet50) as backbone:
        instance = build_model()
        assert backbone.call_args.kwargs["weights"] is None
        return instance


@requires_tf
def test_model_structure_and_names(model):
    assert model.input_shape == (None, 224, 224, 3)
    assert model.output_names == ["type", "acne", "dark", "age"]
    assert model.output_shape == [(None, 3), (None, 1), (None, 1), (None, 1)]
    assert [model.get_layer(n).activation.__name__ for n in model.output_names] == ["softmax", "sigmoid", "sigmoid", "linear"]
    assert SKIN_TYPE_CLASSES == ("Normal", "Dry", "Oily")
    assert not model.get_layer("resnet50").trainable


@requires_tf
def test_synthetic_single_forward_and_no_download(model, tf):
    outputs = model(tf.zeros((1, 224, 224, 3)), training=False)
    assert [tuple(x.shape) for x in outputs] == [(1, 3), (1, 1), (1, 1), (1, 1)]
    assert all(bool(tf.reduce_all(tf.math.is_finite(x))) for x in outputs)


@requires_tf
def test_standard_preprocess_matches_tensorflow(tf):
    rgb = np.array([[[10, 20, 30], [255, 0, 127]]], dtype=np.float32)
    expected = tf.keras.applications.resnet50.preprocess_input(rgb.copy())
    np.testing.assert_allclose(preprocess_image(rgb, version="resnet50_imagenet_v1"), expected, atol=1e-5)


@requires_tf
@pytest.mark.parametrize("task,targets,predictions,expected", [
    ("type", [0, -1, 2], [[0.8, 0.1, 0.1], [0.2, 0.3, 0.5], [0.1, 0.2, 0.7]], -np.log(0.8) - np.log(0.7)),
    ("acne", [1, -1, 0], [[0.8], [0.4], [0.25]], -np.log(0.8) - np.log(0.75)),
    ("dark", [0, -1, 1], [[0.2], [0.4], [0.75]], -np.log(0.8) - np.log(0.75)),
    ("age", [20, -1, 40], [[22], [400], [37]], 13),
])
def test_masked_loss_numerator_and_valid_count(tf, task, targets, predictions, expected):
    from skin_analyzer.masked_losses import masked_loss_stats, normalized_loss
    numerator, count = masked_loss_stats(targets, predictions, task=task)
    assert int(count) == 2
    assert float(numerator) == pytest.approx(expected, rel=1e-5)
    assert float(normalized_loss(numerator, count)) == pytest.approx(expected / 2, rel=1e-5)


@requires_tf
@pytest.mark.parametrize("task,width", [("type", 3), ("acne", 1), ("dark", 1), ("age", 1)])
def test_all_missing_has_zero_loss_and_gradient(tf, task, width):
    from skin_analyzer.masked_losses import masked_loss_stats, normalized_loss
    predictions = tf.Variable(tf.fill((2, width), float("nan")))
    with tf.GradientTape() as tape:
        numerator, count = masked_loss_stats([-1, -1], predictions, task=task)
        loss = normalized_loss(numerator, count)
    gradient = tape.gradient(loss, predictions)
    assert int(count) == 0 and float(loss) == 0
    assert gradient is not None
    np.testing.assert_array_equal(gradient.numpy(), np.zeros((2, width)))


@requires_tf
def test_mixed_masked_nan_has_finite_zero_masked_gradient(tf):
    from skin_analyzer.masked_losses import masked_loss_stats, normalized_loss
    predictions = tf.Variable([[0.8], [float("nan")], [0.25]])
    with tf.GradientTape() as tape:
        loss = normalized_loss(*masked_loss_stats([1, -1, 0], predictions, task="acne"))
    gradient = tape.gradient(loss, predictions).numpy()
    assert np.isfinite(float(loss)) and np.isfinite(gradient).all()
    assert gradient[1, 0] == 0


@requires_tf
def test_aggregate_uses_sums_and_counts(tf):
    from skin_analyzer.masked_losses import masked_loss_stats, normalized_loss
    a, na = masked_loss_stats([0, -1], [[1.0], [0.0]], task="age")
    b, nb = masked_loss_stats([0, 0], [[2.0], [3.0]], task="age")
    assert float(normalized_loss(a + b, na + nb)) == pytest.approx(14 / 3)


@requires_tf
def test_invalid_known_target_fails(tf):
    from skin_analyzer.masked_losses import masked_loss_stats
    with pytest.raises(tf.errors.InvalidArgumentError):
        masked_loss_stats([2], [[0.2]], task="acne")


@requires_tf
def test_weighted_tasks_and_empty_head(tf):
    from skin_analyzer.masked_losses import weighted_task_losses
    targets = {"type": [-1], "acne": [1], "dark": [-1], "age": [3]}
    preds = {"type": [[0.2, 0.3, 0.5]], "acne": [[0.5]], "dark": [[0.5]], "age": [[5.0]]}
    weights = {"type": 1, "acne": 2, "dark": 1, "age": 0.5}
    total, stats = weighted_task_losses(targets, preds, weights)
    assert float(total) == pytest.approx(2 * np.log(2) + 2)
    assert int(stats["dark"][1]) == 0
    with pytest.raises(ValueError):
        weighted_task_losses(targets, preds, {**weights, "age": -1})


@requires_tf
def test_safe_synthetic_model_serialization(model, tf, tmp_path):
    from skin_analyzer.masked_losses import masked_type_loss
    path = tmp_path / "untrained.keras"
    model.save(path)
    restored = tf.keras.models.load_model(path, safe_mode=True, compile=False)
    assert restored.output_names == model.output_names
    assert restored.output_shape == model.output_shape
    config = tf.keras.utils.serialize_keras_object(masked_type_loss)
    assert tf.keras.utils.deserialize_keras_object(config, safe_mode=True) is masked_type_loss
