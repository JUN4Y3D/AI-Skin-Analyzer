from __future__ import annotations

import io
import os

import numpy as np
import pytest
from PIL import Image

from app.config import AppConfig
from app.imaging.face_detection import FaceDetection
from app.inference.artifacts import CLASSES, load_artifacts
from app.inference.models import Predictor, component_outputs
from app.inference.pipeline import AnalysisPipeline


def test_component_math_retains_unrounded_values():
    feature = np.ones(2048, dtype="float32")
    unit = feature / np.linalg.norm(feature)
    age = {"support": np.stack([unit, -unit]), "dual": np.array([5.0, -2.0]), "intercept": np.array(20.0)}
    refs = {
        "acne": {
            "positive_reference_embeddings": np.stack([unit, unit, -unit]),
            "top_k": np.array(2),
            "similarity_threshold_positive_p10": np.array(0.5),
        }
    }
    target, result = component_outputs(feature, age, refs)
    assert target == 27
    assert result["acne"]["similarity"] == pytest.approx(1.0)
    assert result["acne"]["relative_to_positive_reference"] == "at_or_above"


def test_fitted_class_order_matches_phase6n_contract():
    assert CLASSES == ("Dry", "Normal", "Oily")


@pytest.mark.skipif(os.environ.get("AI_SKIN_RUN_PRIVATE_INTEGRATION") != "1", reason="private model integration is opt-in")
def test_private_model_load_and_phase6n_synthetic_regression():
    config = AppConfig()
    artifacts = load_artifacts(config.project_root, config.skin_run, config.components_run)
    predictor = Predictor(artifacts, config.model_version)
    image = Image.new("RGB", (317, 241), (92, 137, 181))
    buffer = io.BytesIO()
    image.save(buffer, format="PNG")
    result = predictor(buffer.getvalue())
    assert result["skin_type"]["label"] == "Normal"
    expected = {"Dry": 0.0229, "Normal": 0.7696, "Oily": 0.2075}
    for name, value in expected.items():
        assert result["skin_type"]["scores"][name] == pytest.approx(value, abs=5e-4)
    assert result["age_like_numeric_target"] == 30
    assert result["positive_references"]["acne"]["similarity"] == pytest.approx(0.239, abs=5e-4)
    assert result["positive_references"]["dark_circle"]["similarity"] == pytest.approx(0.185, abs=5e-4)

    class OneFaceDetector:
        def detect(self, _image):
            return FaceDetection(((75, 35, 150, 170),))

    automatic = AnalysisPipeline(config, predictor, OneFaceDetector()).analyze(buffer.getvalue(), "image/png")
    assert automatic["analysis_input"] == "detected_face_crop"
    assert "original" not in automatic and "mode" not in automatic
    assert automatic["primary"]["skin_type"]["label"] == "Normal"
    assert automatic["primary"]["age_like_numeric_target"] == 30
    assert automatic["primary"]["positive_references"]["acne"]["similarity"] == pytest.approx(0.239, abs=5e-4)
    assert automatic["primary"]["positive_references"]["dark_circle"]["similarity"] == pytest.approx(0.185, abs=5e-4)
