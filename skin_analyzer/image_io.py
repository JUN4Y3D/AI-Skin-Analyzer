"""Non-destructive JPEG/PNG loading and ResNet50 preprocessing."""

from __future__ import annotations

from pathlib import Path
from typing import Tuple

import numpy as np
from PIL import Image, UnidentifiedImageError

from .config import IMAGE_SIZE, SUPPORTED_EXTENSIONS


def load_image(path: Path, size: Tuple[int, int] = IMAGE_SIZE) -> np.ndarray:
    """Load an image as finite RGB float32 pixels in the range [0, 255].

    ``size`` is specified as ``(width, height)``. The original file is opened
    read-only and is never changed.
    """
    if path.suffix.lower() not in SUPPORTED_EXTENSIONS:
        raise ValueError(f"{path}: unsupported image extension {path.suffix!r}")
    try:
        with Image.open(path) as image:
            image.load()
            rgb = image.convert("RGB")
            resized = rgb.resize(size, Image.Resampling.BILINEAR)
            array = np.asarray(resized, dtype=np.float32)
    except (OSError, UnidentifiedImageError) as exc:
        raise ValueError(f"{path}: unable to decode image: {exc}") from exc
    if array.shape != (size[1], size[0], 3):
        raise ValueError(f"{path}: decoded shape {array.shape} is not RGB")
    if not np.isfinite(array).all():
        raise ValueError(f"{path}: decoded pixels contain non-finite values")
    return array


def preprocess_resnet50(image: np.ndarray) -> np.ndarray:
    """Apply Keras ResNet50 ImageNet ``preprocess_input`` in RGB input order.

    This is the documented Keras ``caffe`` preprocessing contract: RGB input
    values in [0, 255] are converted to BGR and centered by ImageNet means.
    The result is float32 with shape ``(height, width, 3)``.
    """
    array = np.asarray(image, dtype=np.float32)
    if array.ndim != 3 or array.shape[-1] != 3:
        raise ValueError(f"expected an image shaped (height, width, 3), got {array.shape}")
    if not np.isfinite(array).all():
        raise ValueError("image contains non-finite values")
    bgr = array[..., ::-1].copy()
    bgr[..., 0] -= 103.939
    bgr[..., 1] -= 116.779
    bgr[..., 2] -= 123.680
    return bgr


PREPROCESSING_VERSIONS = ("legacy_rgb_0_1", "resnet50_imagenet_v1")


def preprocess_image(image: np.ndarray, *, version: str) -> np.ndarray:
    """Transform raw RGB [0,255] pixels; explicit version is mandatory.

    Accepts one image or a batch. Callers must record the version alongside
    model artifacts; values alone cannot identify an already-scaled input.
    """
    if version not in PREPROCESSING_VERSIONS:
        raise ValueError(f"unknown preprocessing version: {version!r}")
    array = np.asarray(image, dtype=np.float32)
    if array.ndim not in (3, 4) or array.shape[-1] != 3:
        raise ValueError("expected RGB image or batch with 3 channels")
    if not np.isfinite(array).all() or np.any(array < 0) or np.any(array > 255):
        raise ValueError("expected finite raw RGB values in [0, 255]")
    if version == "legacy_rgb_0_1":
        return array / np.float32(255.0)
    # The same channel operation as preprocess_resnet50, including batch input.
    bgr = array[..., ::-1].copy()
    bgr -= np.array([103.939, 116.779, 123.680], dtype=np.float32)
    return bgr


def preprocess_for_model(image: np.ndarray, *, version: str, expected_version: str) -> np.ndarray:
    """Fail on a mismatch with the explicitly recorded model preprocessing."""
    if version != expected_version:
        raise ValueError("preprocessing version does not match model metadata")
    return preprocess_image(image, version=version)
