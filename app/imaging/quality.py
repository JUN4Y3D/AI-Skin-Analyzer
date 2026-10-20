"""Transparent, non-clinical image-quality heuristics."""
from __future__ import annotations

from typing import Any

import cv2
import numpy as np
from PIL import Image

from .face_detection import FaceDetection


BLUR_VARIANCE_THRESHOLD = 80.0
UNDEREXPOSED_MEAN_THRESHOLD = 55.0
OVEREXPOSED_MEAN_THRESHOLD = 205.0
EXTREME_PIXEL_RATIO_THRESHOLD = 0.35
MIN_FACE_AREA_RATIO = 0.08


def _warning(code: str, title: str, message: str, severity: str = "warning") -> dict[str, str]:
    return {"code": code, "title": title, "message": message, "severity": severity}


def assess_quality(image: Image.Image, detection: FaceDetection, min_side: int) -> dict[str, Any]:
    rgb = np.asarray(image, dtype="uint8")
    gray = cv2.cvtColor(rgb, cv2.COLOR_RGB2GRAY)
    if max(gray.shape) > 1200:
        scale = 1200 / max(gray.shape)
        gray = cv2.resize(gray, None, fx=scale, fy=scale, interpolation=cv2.INTER_AREA)
    brightness = float(gray.mean())
    dark_ratio = float(np.mean(gray <= 15))
    light_ratio = float(np.mean(gray >= 240))
    blur_variance = float(cv2.Laplacian(gray, cv2.CV_64F).var())
    warnings: list[dict[str, str]] = []

    resolution_acceptable = min(image.size) >= min_side
    if not resolution_acceptable:
        warnings.append(
            _warning(
                "low_resolution",
                "Resolution may be limiting",
                f"The shorter image side is {min(image.size)} px; {min_side} px or more is recommended.",
            )
        )

    if brightness < UNDEREXPOSED_MEAN_THRESHOLD or dark_ratio > EXTREME_PIXEL_RATIO_THRESHOLD:
        brightness_status = "underexposed"
        warnings.append(_warning("underexposed", "Image appears dark", "Try softer, even front lighting and avoid strong backlighting."))
    elif brightness > OVEREXPOSED_MEAN_THRESHOLD or light_ratio > EXTREME_PIXEL_RATIO_THRESHOLD:
        brightness_status = "overexposed"
        warnings.append(_warning("overexposed", "Image appears very bright", "Reduce direct glare and avoid washed-out highlights."))
    else:
        brightness_status = "acceptable"

    blur_status = "possibly_blurry" if blur_variance < BLUR_VARIANCE_THRESHOLD else "acceptable"
    if blur_status != "acceptable":
        warnings.append(_warning("possibly_blurry", "Image may be soft or blurry", "Hold the camera steady and keep the face in focus."))

    face_area_ratio = None
    if detection.status == "no_face":
        warnings.append(
            _warning(
                "no_face",
                "No frontal face detected",
                "Choose a clear, front-facing single-person image; analysis requires a detected facial region.",
            )
        )
    elif detection.status == "multiple_faces":
        warnings.append(
            _warning(
                "multiple_faces",
                "More than one possible face detected",
                "Choose a single-person photograph so the intended subject is not ambiguous.",
                "error",
            )
        )
    else:
        _, _, face_width, face_height = detection.boxes[0]
        face_area_ratio = (face_width * face_height) / (image.width * image.height)
        if face_area_ratio < MIN_FACE_AREA_RATIO:
            warnings.append(
                _warning(
                    "face_too_small",
                    "Face occupies a small part of the frame",
                    "Move closer or use a higher-resolution photograph for more visible detail.",
                )
            )

    return {
        "warnings": warnings,
        "resolution_acceptable": resolution_acceptable,
        "brightness_status": brightness_status,
        "brightness_mean": brightness,
        "dark_pixel_ratio": dark_ratio,
        "light_pixel_ratio": light_ratio,
        "blur_status": blur_status,
        "blur_variance": blur_variance,
        "face_area_ratio": face_area_ratio,
        "heuristics_are_clinically_validated": False,
    }
