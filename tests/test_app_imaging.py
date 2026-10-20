from __future__ import annotations

import io

import pytest
from PIL import Image

from app.config import AppConfig
from app.imaging.face_detection import FaceDetection, crop_single_face, square_crop_box
from app.imaging.quality import assess_quality
from app.imaging.validation import decode_image
from app.inference.pipeline import AnalysisPipeline


def image_bytes(fmt="PNG", size=(640, 640), color=(110, 140, 150), exif=None):
    buffer = io.BytesIO()
    image = Image.new("RGB", size, color)
    options = {"format": fmt}
    if exif is not None:
        options["exif"] = exif
    image.save(buffer, **options)
    return buffer.getvalue()


@pytest.mark.parametrize(("fmt", "media_type"), [("JPEG", "image/jpeg"), ("PNG", "image/png")])
def test_decode_accepts_jpeg_and_png(fmt, media_type):
    raw = image_bytes(fmt)
    decoded = decode_image(raw, media_type, max_bytes=10_000_000, max_pixels=20_000_000)
    assert decoded.image.mode == "RGB"
    assert decoded.image.size == (640, 640)
    assert decoded.source_format == fmt


@pytest.mark.parametrize(
    ("raw", "media_type", "message"),
    [
        (b"", "image/png", "non-empty"),
        (b"not an image", "image/png", "does not match"),
        (image_bytes("PNG"), "image/gif", "Only JPEG and PNG"),
    ],
)
def test_decode_rejects_empty_corrupt_and_unexpected_format(raw, media_type, message):
    with pytest.raises(ValueError, match=message):
        decode_image(raw, media_type, max_bytes=10_000_000, max_pixels=20_000_000)


def test_decode_enforces_byte_and_pixel_limits():
    raw = image_bytes("PNG", (80, 80))
    with pytest.raises(ValueError, match="10 MB"):
        decode_image(raw, "image/png", max_bytes=len(raw) - 1, max_pixels=20_000_000)
    with pytest.raises(ValueError, match="20-megapixel"):
        decode_image(raw, "image/png", max_bytes=10_000_000, max_pixels=100)


def test_exif_orientation_is_applied_in_memory():
    exif = Image.Exif()
    exif[274] = 6
    raw = image_bytes("JPEG", (80, 40), exif=exif)
    decoded = decode_image(raw, "image/jpeg", max_bytes=10_000_000, max_pixels=20_000_000)
    assert decoded.image.size == (40, 80)
    assert decoded.exif_orientation_applied is True
    assert decoded.inference_bytes.startswith(b"\x89PNG")


def test_square_crop_stays_in_bounds_and_rejects_invalid_boxes():
    assert square_crop_box((400, 300), (140, 90, 80, 90)) == (99, 58, 261, 220)
    with pytest.raises(ValueError, match="bounds"):
        square_crop_box((100, 100), (90, 90, 20, 20))


def test_crop_refuses_missing_and_multiple_faces():
    image = Image.new("RGB", (640, 640))
    with pytest.raises(ValueError, match="No frontal face"):
        crop_single_face(image, FaceDetection(()))
    with pytest.raises(ValueError, match="Multiple"):
        crop_single_face(image, FaceDetection(((10, 10, 100, 100), (200, 10, 100, 100))))


def test_quality_reports_resolution_brightness_blur_and_face_states():
    dark = Image.new("RGB", (300, 300), (2, 2, 2))
    result = assess_quality(dark, FaceDetection(()), min_side=512)
    codes = {warning["code"] for warning in result["warnings"]}
    assert {"low_resolution", "underexposed", "possibly_blurry", "no_face"} <= codes
    assert result["heuristics_are_clinically_validated"] is False


class StubDetector:
    def __init__(self, detection):
        self.detection = detection

    def detect(self, _image):
        return self.detection


def fake_prediction(_raw):
    return {
        "skin_type": {"label": "Normal", "scores": {"Dry": 0.1, "Normal": 0.8, "Oily": 0.1}},
        "age_like_numeric_target": 27,
        "positive_references": {
            "acne": {"similarity": 0.2, "positive_reference_p10": 0.7, "relative_to_positive_reference": "below"},
            "dark_circle": {"similarity": 0.3, "positive_reference_p10": 0.8, "relative_to_positive_reference": "below"},
        },
        "model_version": "synthetic",
    }


def test_pipeline_uses_one_cropped_image_for_all_outputs():
    detection = FaceDetection(((180, 150, 260, 280),))
    calls = []

    def recording_prediction(raw):
        calls.append(raw)
        return fake_prediction(raw)

    pipeline = AnalysisPipeline(AppConfig(), recording_prediction, StubDetector(detection))
    raw = image_bytes("PNG")
    result = pipeline.analyze(raw, "image/png")
    assert result["analysis_input"] == "detected_face_crop"
    assert result["crop_preview"].startswith("data:image/jpeg;base64,")
    assert result["primary"]["skin_type"]["label"] == "Normal"
    assert result["primary"]["age_like_numeric_target"] == 27
    assert set(result["primary"]["positive_references"]) == {"acne", "dark_circle"}
    assert result["privacy"] == {"processed_locally": True, "image_persisted": False}
    assert len(calls) == 1
    analyzed = Image.open(io.BytesIO(calls[0]))
    assert analyzed.size == tuple(result["crop_dimensions"])
    assert analyzed.size != (640, 640)
    assert calls[0] != raw


@pytest.mark.parametrize(
    ("detection", "message"),
    [
        (FaceDetection(()), "No frontal face"),
        (FaceDetection(((10, 10, 150, 150), (300, 10, 150, 150))), "Multiple"),
    ],
)
def test_pipeline_refuses_missing_or_ambiguous_faces_without_inference(detection, message):
    calls = []
    pipeline = AnalysisPipeline(AppConfig(), lambda raw: calls.append(raw), StubDetector(detection))
    with pytest.raises(ValueError, match=message):
        pipeline.analyze(image_bytes(), "image/png")
    assert calls == []
