"""Shared upload/camera pipeline with mandatory in-memory face cropping."""
from __future__ import annotations

import time
from typing import Any, Callable

from app.config import AppConfig
from app.imaging.face_detection import FaceDetector, crop_single_face, image_as_png, preview_data_uri
from app.imaging.quality import assess_quality
from app.imaging.validation import DecodedImage, decode_image


class AnalysisPipeline:
    def __init__(
        self,
        config: AppConfig,
        predictor: Callable[[bytes], dict[str, Any]],
        face_detector: FaceDetector | None = None,
    ):
        self.config = config
        self.predictor = predictor
        self.face_detector = face_detector or FaceDetector()

    def _decode(self, raw: bytes, content_type: str) -> DecodedImage:
        return decode_image(
            raw,
            content_type,
            max_bytes=self.config.max_image_bytes,
            max_pixels=self.config.max_pixels,
        )

    def analyze(self, raw: bytes, content_type: str) -> dict[str, Any]:
        """Detect one face, crop it, and run every fitted component once."""
        started = time.perf_counter()
        decoded = self._decode(raw, content_type)
        detection = self.face_detector.detect(decoded.image)
        quality = assess_quality(decoded.image, detection, self.config.min_image_side)
        cropped, rectangle = crop_single_face(decoded.image, detection)
        cropped_bytes = image_as_png(cropped)
        primary = self.predictor(cropped_bytes)

        review = {
            "source": {
                "dimensions": [decoded.width, decoded.height],
                "bytes": decoded.byte_length,
                "format": decoded.source_format,
                "exif_orientation_applied": decoded.exif_orientation_applied,
            },
            "face_detection": {
                "status": detection.status,
                "count": len(detection.boxes),
                "crop_available": True,
                "crop_dimensions": [cropped.width, cropped.height],
                "crop_rectangle": list(rectangle),
            },
            "quality": quality,
        }

        elapsed_ms = (time.perf_counter() - started) * 1000
        return {
            "analysis_input": "detected_face_crop",
            "primary": primary,
            "crop_preview": preview_data_uri(cropped),
            "crop_dimensions": [cropped.width, cropped.height],
            "crop_rectangle": list(rectangle),
            "detected_faces": review["face_detection"]["count"],
            "review": review,
            "inference_duration_ms": elapsed_ms,
            "privacy": {"processed_locally": True, "image_persisted": False},
        }
