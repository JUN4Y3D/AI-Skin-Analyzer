"""Deterministic local OpenCV face detection and crop helpers."""
from __future__ import annotations

import base64
import io
from dataclasses import dataclass
from pathlib import Path

import cv2
import numpy as np
from PIL import Image


@dataclass(frozen=True)
class FaceDetection:
    boxes: tuple[tuple[int, int, int, int], ...]

    @property
    def status(self) -> str:
        if not self.boxes:
            return "no_face"
        if len(self.boxes) == 1:
            return "single_face"
        return "multiple_faces"


def square_crop_box(size: tuple[int, int], face_box: tuple[int, int, int, int]) -> tuple[int, int, int, int]:
    width, height = size
    x, y, face_width, face_height = face_box
    if (
        width < 1
        or height < 1
        or face_width < 1
        or face_height < 1
        or x < 0
        or y < 0
        or x + face_width > width
        or y + face_height > height
    ):
        raise ValueError("Invalid detected face bounds")
    side = min(min(width, height), max(face_width, face_height) * 1.8)
    center_x = x + face_width / 2
    center_y = y + face_height / 2 + face_height * 0.04
    left = max(0, min(width - side, center_x - side / 2))
    top = max(0, min(height - side, center_y - side / 2))
    left, top, side = int(round(left)), int(round(top)), int(round(side))
    right, bottom = min(width, left + side), min(height, top + side)
    if right - left < 64 or bottom - top < 64:
        raise ValueError("Detected face region is too small for a useful crop")
    return left, top, right, bottom


class FaceDetector:
    def __init__(self):
        cascade_path = Path(cv2.data.haarcascades) / "haarcascade_frontalface_default.xml"
        self.classifier = cv2.CascadeClassifier(str(cascade_path))
        if self.classifier.empty():
            raise ValueError("OpenCV frontal-face detector is unavailable")

    def detect(self, image: Image.Image) -> FaceDetection:
        width, height = image.size
        factor = min(1.0, 1200.0 / max(width, height))
        if factor < 1:
            preview = image.resize(
                (max(1, int(width * factor)), max(1, int(height * factor))),
                Image.Resampling.BILINEAR,
            )
        else:
            preview = image
        frame = np.asarray(preview, dtype="uint8")
        gray = cv2.equalizeHist(cv2.cvtColor(frame, cv2.COLOR_RGB2GRAY))
        minimum = max(36, int(min(gray.shape) * 0.065))
        found = self.classifier.detectMultiScale(
            gray,
            scaleFactor=1.1,
            minNeighbors=5,
            minSize=(minimum, minimum),
        )
        boxes = []
        for raw_x, raw_y, raw_w, raw_h in found:
            x = int(round(int(raw_x) / factor))
            y = int(round(int(raw_y) / factor))
            box_width = max(1, int(round(int(raw_w) / factor)))
            box_height = max(1, int(round(int(raw_h) / factor)))
            boxes.append((x, y, min(box_width, width - x), min(box_height, height - y)))
        boxes.sort(key=lambda box: box[2] * box[3], reverse=True)
        return FaceDetection(tuple(boxes))


def crop_single_face(image: Image.Image, detection: FaceDetection) -> tuple[Image.Image, tuple[int, int, int, int]]:
    if detection.status == "no_face":
        raise ValueError("No frontal face was detected. Retake or upload a clearer front-facing single-person image")
    if detection.status == "multiple_faces":
        raise ValueError("Multiple possible faces were detected. Use a photograph containing one person")
    rectangle = square_crop_box(image.size, detection.boxes[0])
    return image.crop(rectangle), rectangle


def image_as_png(image: Image.Image) -> bytes:
    buffer = io.BytesIO()
    image.save(buffer, format="PNG")
    return buffer.getvalue()


def preview_data_uri(image: Image.Image, max_side: int = 640) -> str:
    preview = image.copy()
    preview.thumbnail((max_side, max_side), Image.Resampling.LANCZOS)
    buffer = io.BytesIO()
    preview.save(buffer, format="JPEG", quality=84, optimize=True)
    payload = base64.b64encode(buffer.getvalue()).decode("ascii")
    return f"data:image/jpeg;base64,{payload}"
