#!/usr/bin/env python3
"""Download and verify AI Skin Analyzer's published model artifacts."""

import hashlib
import shutil
import tempfile
from pathlib import Path
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen
from zipfile import ZipFile

ROOT = Path(__file__).resolve().parents[1]
URL = (
    "https://github.com/JUN4Y3D/AI-Skin-Analyzer/"
    "releases/download/models-v1/ai-skin-models-v1.zip"
)
EXPECTED_SHA256 = (
    "bb9c03d017099851434146df23f0f78c0feff9073dfc3785e1a30853f7a0a9b6"
)

BASE = "reports/private/phase6_training_runs"
SKIN = "skin_type_phase6k_finetune_83076473ef76"
OTHER = "phase6l_other_components_1e261ce2d702"

EXPECTED = {
    "reports/private/hosted_provenance_sha256.json",
    f"{BASE}/{SKIN}/best_development_model.keras",
    f"{BASE}/{SKIN}/development_metrics.json",
    f"{BASE}/{OTHER}/prototype_metrics.json",
    f"{BASE}/{OTHER}/age_like_ridge.npz",
    f"{BASE}/{OTHER}/acne_positive_reference.npz",
    f"{BASE}/{OTHER}/dark_circle_positive_reference.npz",
}


def main():
    target = ROOT / "reports/private"

    if target.exists() or target.is_symlink():
        raise SystemExit(
            "Model directory already exists. Refusing to overwrite it."
        )

    with tempfile.TemporaryDirectory() as temporary:
        tmp = Path(temporary)
        archive = tmp / "models.zip"

        print("Downloading trained model package...")
        digest = hashlib.sha256()
        downloaded = 0

        request = Request(
            URL,
            headers={"User-Agent": "AI-Skin-Analyzer-Installer"},
        )

        try:
            with urlopen(request, timeout=60) as response:
                with archive.open("wb") as output:
                    while True:
                        chunk = response.read(1024 * 1024)
                        if not chunk:
                            break
                        downloaded += len(chunk)
                        if downloaded > 200 * 1024 * 1024:
                            raise ValueError("Download exceeds size limit")
                        digest.update(chunk)
                        output.write(chunk)
        except HTTPError as error:
            if error.code == 404:
                raise SystemExit(
                    "Model release is not public yet."
                ) from None
            raise SystemExit(f"Download failed: HTTP {error.code}")
        except URLError as error:
            raise SystemExit(f"Network error: {error.reason}")

        if digest.hexdigest() != EXPECTED_SHA256:
            raise SystemExit("Model package checksum mismatch!")

        with ZipFile(archive) as zf:
            files = zf.infolist()

            if (
                len(files) != len(EXPECTED)
                or {item.filename for item in files} != EXPECTED
                or any(item.is_dir() for item in files)
                or sum(item.file_size for item in files) > 200 * 1024 * 1024
            ):
                raise SystemExit("Unexpected model archive contents!")

            for item in files:
                relative = Path(item.filename)
                destination = tmp / relative
                destination.parent.mkdir(parents=True, exist_ok=True)

                with zf.open(item) as source:
                    with destination.open("wb") as output:
                        shutil.copyfileobj(source, output)

        target.parent.mkdir(parents=True, exist_ok=True)

        if target.exists() or target.is_symlink():
            raise SystemExit("Model directory appeared during installation.")

        (tmp / "reports/private").rename(target)

    print("PASS: Seven trained-model artifacts installed.")
    print("PASS: SHA-256 verified.")
    print("Next: python scripts/run_app.py --check")


if __name__ == "__main__":
    main()
