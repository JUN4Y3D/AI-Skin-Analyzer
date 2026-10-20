"""TensorFlow and fitted-component inference with Phase 6N parity."""
from __future__ import annotations

import os
import threading
from typing import Any

import numpy as np

from .artifacts import ArtifactBundle, CLASSES


def _unit_feature(feature: np.ndarray) -> np.ndarray:
    vector = np.asarray(feature, dtype="float64").reshape(-1)
    if vector.shape != (2048,) or not np.isfinite(vector).all():
        raise ValueError("Unexpected encoder output")
    magnitude = float(np.linalg.norm(vector))
    if magnitude < 1e-9:
        raise ValueError("Degenerate encoder output")
    return vector / magnitude


def component_outputs(
    feature: np.ndarray,
    age: dict[str, np.ndarray],
    references: dict[str, dict[str, np.ndarray]],
) -> tuple[int, dict[str, dict[str, float | str]]]:
    """Compute outputs without display rounding."""
    vector = _unit_feature(feature)
    support = np.asarray(age["support"], dtype="float64")
    dual = np.asarray(age["dual"], dtype="float64")
    numeric = float(np.clip(float(age["intercept"]) + (support @ vector) @ dual, 0, 120))
    similarities: dict[str, dict[str, float | str]] = {}
    for name, arrays in references.items():
        embeddings = np.asarray(arrays["positive_reference_embeddings"], dtype="float64")
        top_k = int(arrays["top_k"])
        scores = embeddings @ vector
        similarity = float(np.mean(np.partition(scores, -top_k)[-top_k:]))
        benchmark = float(arrays["similarity_threshold_positive_p10"])
        similarities[name] = {
            "similarity": similarity,
            "positive_reference_p10": benchmark,
            "relative_to_positive_reference": "at_or_above" if similarity >= benchmark else "below",
        }
    return int(round(numeric)), similarities


class Predictor:
    """Load the private model once and serialize inference through a lock."""

    def __init__(self, artifacts: ArtifactBundle, model_version: str):
        os.environ.setdefault("TF_CPP_MIN_LOG_LEVEL", "2")
        import tensorflow as tf

        self.tf = tf
        self.model_version = model_version
        self.model = tf.keras.models.load_model(str(artifacts.model_path), compile=False, safe_mode=True)
        if tuple(self.model.input_shape[1:]) != (224, 224, 3) or tuple(self.model.output_shape[1:]) != (3,):
            raise ValueError("Unexpected skin-type model input/output dimensions")
        candidates = [
            layer
            for layer in self.model.layers
            if isinstance(layer, tf.keras.Model) and "resnet" in layer.name.lower()
        ]
        if len(candidates) != 1 or tuple(candidates[0].output_shape[1:]) != (2048,):
            raise ValueError("Cannot identify the compatible pooled ResNet50 backbone")
        self.backbone = candidates[0]
        self.age = artifacts.age
        self.references = artifacts.references
        self.lock = threading.Lock()

    def __call__(self, raw: bytes) -> dict[str, Any]:
        tf = self.tf
        image = tf.io.decode_image(raw, channels=3, expand_animations=False)
        image.set_shape((None, None, 3))
        resized = tf.image.resize(tf.cast(image, tf.float32), (224, 224))
        batch = tf.keras.applications.resnet50.preprocess_input(tf.expand_dims(resized, 0))
        with self.lock:
            probabilities = np.asarray(self.model(batch, training=False).numpy()[0], dtype="float64")
            embedding = np.asarray(self.backbone(batch, training=False).numpy()[0], dtype="float64")
        if (
            probabilities.shape != (3,)
            or not np.isfinite(probabilities).all()
            or not np.isclose(probabilities.sum(), 1, atol=1e-3)
        ):
            raise ValueError("Unexpected skin-type scores")
        age_like, similarities = component_outputs(embedding, self.age, self.references)
        return {
            "skin_type": {
                "label": CLASSES[int(probabilities.argmax())],
                "scores": {name: float(value) for name, value in zip(CLASSES, probabilities)},
                "scores_are_calibrated": False,
            },
            "age_like_numeric_target": age_like,
            "positive_references": similarities,
            "model_version": self.model_version,
        }
