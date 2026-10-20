import numpy as np
import pytest
from PIL import Image

from skin_analyzer.image_io import load_image, preprocess_resnet50, preprocess_image, preprocess_for_model


@pytest.mark.parametrize("extension", [".jpg", ".png"])
def test_load_image_supports_jpeg_and_png_rgb(tmp_path, extension):
    path = tmp_path / f"synthetic{extension}"
    mode = "RGB" if extension == ".jpg" else "RGBA"
    Image.new(mode, (8, 4), (10, 20, 30, 255) if mode == "RGBA" else (10, 20, 30)).save(path)
    image = load_image(path, size=(4, 3))
    assert image.shape == (3, 4, 3)
    assert image.dtype == np.float32
    assert np.isfinite(image).all()


def test_invalid_image_includes_filename(tmp_path):
    path = tmp_path / "broken.jpg"
    path.write_bytes(b"not an image")
    with pytest.raises(ValueError, match="broken.jpg"):
        load_image(path)


def test_resnet_preprocessing_is_finite_and_preserves_shape():
    image = np.full((2, 3, 3), 255, dtype=np.uint8)
    processed = preprocess_resnet50(image)
    assert processed.shape == image.shape
    assert processed.dtype == np.float32
    assert np.isfinite(processed).all()
    assert np.allclose(processed[0, 0], [151.061, 138.221, 131.32], atol=1e-3)


def test_versioned_preprocessing_distinguishes_contracts_and_batches():
    image = np.array([[[255, 100, 0]]], dtype=np.float32)
    legacy = preprocess_image(image, version="legacy_rgb_0_1")
    standard = preprocess_image(image, version="resnet50_imagenet_v1")
    assert np.allclose(legacy[0, 0], [1, 100 / 255, 0])
    assert np.allclose(standard[0, 0], [-103.939, -16.779, 131.32], atol=1e-4)
    assert np.allclose(standard, preprocess_resnet50(image))
    assert np.allclose(preprocess_image(image[None], version="resnet50_imagenet_v1")[0], standard)
    assert not np.allclose(legacy, standard)


def test_preprocessing_requires_known_version_and_raw_shape():
    with pytest.raises(TypeError):
        preprocess_image(np.zeros((1, 1, 3)))
    with pytest.raises(ValueError):
        preprocess_image(np.zeros((1, 1, 3)), version="unknown")
    with pytest.raises(ValueError):
        preprocess_image(np.full((1, 1, 3), 256), version="legacy_rgb_0_1")
    with pytest.raises(ValueError):
        preprocess_image(np.zeros((1, 1)), version="legacy_rgb_0_1")
    with pytest.raises(ValueError, match="does not match"):
        preprocess_for_model(np.zeros((1, 1, 3)), version="legacy_rgb_0_1", expected_version="resnet50_imagenet_v1")
