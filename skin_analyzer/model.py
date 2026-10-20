"""Untrained four-head model definition. TensorFlow is an optional dependency."""

from __future__ import annotations

from .model_contract import INPUT_SHAPE


def build_model(*, weights: str | None = None, backbone_trainable: bool = False):
    """Build an uncompiled baseline; pretrained weights are deliberately disabled.

    ``weights='imagenet'`` is reserved for a separately approved future phase;
    it is blocked here rather than potentially triggering a network download.
    Callers must explicitly select and record a preprocessing version separately.
    """
    if weights is not None:
        raise ValueError("pretrained weights are disabled; only weights=None is allowed")
    try:
        import tensorflow as tf
    except ImportError as exc:
        raise ImportError("model construction requires the optional TensorFlow dependency") from exc

    inputs = tf.keras.Input(shape=INPUT_SHAPE, name="image")
    backbone = tf.keras.applications.ResNet50(
        include_top=False, weights=None, input_shape=INPUT_SHAPE
    )
    backbone.trainable = backbone_trainable
    features = tf.keras.layers.GlobalAveragePooling2D(name="shared_pool")(backbone(inputs))
    outputs = []
    for name, hidden, units, activation in (
        ("type", 128, 3, "softmax"),
        ("acne", 64, 1, "sigmoid"),
        ("dark", 64, 1, "sigmoid"),
        ("age", 64, 1, "linear"),
    ):
        branch = tf.keras.layers.Dense(hidden, activation="relu", name=f"{name}_hidden")(features)
        outputs.append(tf.keras.layers.Dense(units, activation=activation, name=name)(branch))
    return tf.keras.Model(inputs=inputs, outputs=outputs, name="skin_analyzer_resnet50")
