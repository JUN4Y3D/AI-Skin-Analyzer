"""TensorFlow-only partial-label primitives; not a training implementation.

Statistics are batch sums and counts. Aggregate sums and counts across batches
before dividing for a dataset-wide mean; never average batch means equally.
"""
from __future__ import annotations

from collections.abc import Mapping
import math

import tensorflow as tf

TASKS = ("type", "acne", "dark", "age")


def masked_loss_stats(y_true, y_pred, *, task: str):
    """Return scalar (sum of valid losses, valid count) for a single head.

    Labels are -1 for missing, [0,1,2] for type, [0,1] for binary, and
    finite numeric for age. Invalid nonmissing labels fail rather than vanish.
    Only valid predictions enter the loss, preventing masked NaNs and gradients.
    """
    if task not in TASKS:
        raise ValueError(f"unknown task: {task!r}")
    predictions = tf.cast(tf.convert_to_tensor(y_pred), tf.float32)
    targets = tf.cast(tf.reshape(tf.convert_to_tensor(y_true), [-1]), tf.float32)
    tf.debugging.assert_rank(predictions, 2)
    tf.debugging.assert_equal(tf.shape(predictions)[0], tf.size(targets))
    tf.debugging.assert_equal(tf.shape(predictions)[1], 3 if task == "type" else 1)
    mask = tf.not_equal(targets, -1.0)
    valid_targets = tf.boolean_mask(targets, mask)
    valid_predictions = tf.boolean_mask(predictions, mask)
    tf.debugging.assert_all_finite(valid_targets, "non-finite targets")
    tf.debugging.assert_all_finite(valid_predictions, "non-finite valid predictions")
    if task in ("type", "acne", "dark"):
        tf.debugging.assert_equal(valid_targets, tf.round(valid_targets), message="labels must be integers")
        tf.debugging.assert_greater_equal(valid_targets, 0.0)
        tf.debugging.assert_less_equal(valid_targets, 2.0 if task == "type" else 1.0)
    count = tf.size(valid_targets, out_type=tf.int64)

    def nonempty():
        if task == "type":
            values = tf.keras.losses.sparse_categorical_crossentropy(
                tf.cast(valid_targets, tf.int32), valid_predictions
            )
        elif task in ("acne", "dark"):
            values = tf.keras.losses.binary_crossentropy(
                tf.expand_dims(valid_targets, -1), valid_predictions
            )
        else:
            values = tf.square(valid_targets - tf.squeeze(valid_predictions, axis=-1))
        return tf.reduce_sum(values)

    # Gathered empty tensor keeps a zero-gradient path to predictions.
    numerator = tf.cond(count > 0, nonempty, lambda: tf.reduce_sum(valid_predictions))
    return numerator, count


def normalized_loss(numerator, count):
    """Return zero when count is zero, otherwise sum / count."""
    return tf.math.divide_no_nan(numerator, tf.cast(count, numerator.dtype))


def weighted_task_losses(targets: Mapping, predictions: Mapping, weights: Mapping):
    """Return weighted sum and raw per-task stats; weights are explicit scalars."""
    if set(targets) != set(TASKS) or set(predictions) != set(TASKS) or set(weights) != set(TASKS):
        raise ValueError("targets, predictions and weights must contain exactly the four task names")
    if any(not math.isfinite(float(weights[name])) or float(weights[name]) < 0 for name in TASKS):
        raise ValueError("task weights must be finite and nonnegative")
    stats = {name: masked_loss_stats(targets[name], predictions[name], task=name) for name in TASKS}
    total = tf.add_n([tf.cast(weights[name], tf.float32) * normalized_loss(*stats[name]) for name in TASKS])
    return total, stats


# Named components permit safe Keras object serialization; batch-normalized
# losses alone must not be used as dataset-wide metrics.
@tf.keras.utils.register_keras_serializable(package="skin_analyzer")
def masked_type_loss(y_true, y_pred):
    return normalized_loss(*masked_loss_stats(y_true, y_pred, task="type"))


@tf.keras.utils.register_keras_serializable(package="skin_analyzer")
def masked_acne_loss(y_true, y_pred):
    return normalized_loss(*masked_loss_stats(y_true, y_pred, task="acne"))


@tf.keras.utils.register_keras_serializable(package="skin_analyzer")
def masked_dark_loss(y_true, y_pred):
    return normalized_loss(*masked_loss_stats(y_true, y_pred, task="dark"))


@tf.keras.utils.register_keras_serializable(package="skin_analyzer")
def masked_age_loss(y_true, y_pred):
    return normalized_loss(*masked_loss_stats(y_true, y_pred, task="age"))
