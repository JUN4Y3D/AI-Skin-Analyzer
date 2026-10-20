"""Strict, in-memory JPEG/PNG decoding and EXIF orientation handling."""
from __future__ import annotations

import io
from dataclasses import dataclass

from PIL import Image, ImageOps, UnidentifiedImageError


ALLOWED_TYPES = {"image/jpeg": "JPEG", "image/png": "PNG"}


@dataclass(frozen=True)
class DecodedImage:
    image: Image.Image
    inference_bytes: bytes
    media_type: str
    source_format: str
    width: int
    height: int
    byte_length: int
    exif_orientation_applied: bool


def decode_image(raw: bytes, content_type: str, *, max_bytes: int, max_pixels: int) -> DecodedImage:
    kind = content_type.split(";", 1)[0].strip().lower()
    if not raw:
        raise ValueError("Choose a non-empty JPEG or PNG image")
    if len(raw) > max_bytes:
        raise ValueError("Image must be 10 MB or smaller")
    expected = ALLOWED_TYPES.get(kind)
    if expected is None:
        raise ValueError("Only JPEG and PNG images are accepted")
    signature_ok = (expected == "JPEG" and raw.startswith(b"\xff\xd8\xff")) or (
        expected == "PNG" and raw.startswith(b"\x89PNG\r\n\x1a\n")
    )
    if not signature_ok:
        raise ValueError("The file content does not match its declared image type")
    try:
        with Image.open(io.BytesIO(raw)) as source:
            if source.format != expected:
                raise ValueError("The decoded image type is not supported")
            width, height = source.size
            if width < 1 or height < 1 or width * height > max_pixels:
                raise ValueError("Image dimensions exceed the 20-megapixel safety limit")
            orientation = int(source.getexif().get(274, 1) or 1)
            source.load()
            oriented = ImageOps.exif_transpose(source).convert("RGB")
    except (UnidentifiedImageError, OSError, Image.DecompressionBombError) as exc:
        raise ValueError("Invalid or unsafe image file") from exc

    transformed = orientation not in (0, 1)
    inference_bytes = raw
    if transformed:
        buffer = io.BytesIO()
        oriented.save(buffer, format="PNG", optimize=False)
        inference_bytes = buffer.getvalue()
        kind = "image/png"
    return DecodedImage(
        image=oriented,
        inference_bytes=inference_bytes,
        media_type=kind,
        source_format=expected,
        width=oriented.width,
        height=oriented.height,
        byte_length=len(raw),
        exif_orientation_applied=transformed,
    )
