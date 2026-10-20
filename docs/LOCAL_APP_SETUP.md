# Local application setup

## Verified runtime

The verified macOS Apple Silicon environment uses Python 3.12.9, TensorFlow 2.16.2, Keras 3.3.3, NumPy 1.26.4, OpenCV headless 4.10.0, and a compatible Pillow 10.4–13.x release. The virtual environment is intentionally maintained outside the Desktop project directory.

```bash
source ~/Developer/venvs/ai-skin-analyzer/bin/activate
cd /path/to/AI_Skin_Analyzer
python -m pip check
python scripts/run_app.py --check
python scripts/run_app.py
```

`--check` validates private artifact integrity without loading TensorFlow or processing an image. The normal command loads the fitted components once and prints a private loopback URL.

Useful options:

```bash
python scripts/run_app.py --self-test
python scripts/run_app.py --no-open
python scripts/run_app.py --port 8765
```

Do not bind the application to a public interface. Do not put it behind a tunnel or expose it to a phone or another computer without a separately reviewed security and deployment design.

## Tests

```bash
python -m pytest -p no:cacheprovider
AI_SKIN_RUN_PRIVATE_INTEGRATION=1 python -m pytest -p no:cacheprovider tests/test_app_inference.py
```

The opt-in test loads private fitted artifacts and performs one synthetic inference. It does not use the private facial dataset.

## New environments

Only create or install into a new environment after explicit approval:

```bash
python -m pip install -e '.[ml,app,dev]'
```

Do not silently change the TensorFlow/Keras versions. Do not download pretrained weights; the app uses the existing private fitted checkpoint.

## Camera troubleshooting

- Camera access begins only after **Take Photo**.
- If permission is denied, update the site permission for the loopback origin and macOS camera permissions, then retry.
- Close other applications using the camera if the browser reports it is busy.
- Use Upload Photo if camera APIs are unavailable.
- The front-camera preview and captured frame are intentionally mirrored together.
- Camera tracks stop when switching to upload, leaving capture, or closing the page.
