"""Project-wide data pipeline configuration."""

from __future__ import annotations

from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
SPLITS = ("train", "val", "test")
REQUIRED_COLUMNS = (
    "filename",
    "skin_type",
    "has_acne",
    "has_dark_circle",
    "skin_age",
)
IMAGE_SIZE = (224, 224)
SUPPORTED_EXTENSIONS = {".jpg", ".jpeg", ".png"}
