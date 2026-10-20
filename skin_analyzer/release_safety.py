"""Conservative, offline release screening; passing is not legal approval.

The inventory must remain private. No detected value or private path is printed.
"""
from __future__ import annotations

import argparse
import csv
import json
import os
from pathlib import Path, PurePosixPath
import re

PRIVATE_DIRS = {"train", "val", "test", "labels", "private", ".git", ".venv", "venv", "__pycache__", ".pytest_cache", "outputs", "predictions"}
TEXT_SUFFIXES = {
    ".py",
    ".md",
    ".toml",
    ".yaml",
    ".yml",
    ".txt",
    ".csv",
    ".html",
    ".css",
    ".js",
    ".mjs",
    ".json",
}
BLOCKED_SUFFIXES = {".jpg", ".jpeg", ".png", ".gif", ".webp", ".bmp", ".tif", ".tiff", ".h5", ".hdf5", ".keras", ".onnx", ".pb", ".tflite", ".ckpt", ".pt", ".pth", ".pkl", ".pickle", ".npz", ".npy", ".zip", ".tar", ".gz", ".key", ".pem"}
_BACKSLASH = re.escape(chr(92))
LOCAL_PATH = re.compile(
    r"(?<![A-Za-z0-9_.-])/(?:Users|home|content/drive|private)/"
    + r"|[A-Za-z]:"
    + _BACKSLASH
    + "|"
    + _BACKSLASH * 2
    + r"[A-Za-z0-9._-]+"
)
SECRET = re.compile(r"(?:AKIA[0-9A-Z]{16}|-----BEGIN (?:RSA |EC |OPENSSH )?PRIVATE KEY-----|\bsk-[A-Za-z0-9_-]{20,}|(?:api[_-]?key|password|secret|token)\s*[:=]\s*['\"][A-Za-z0-9_/-]{16,}['\"])", re.I)
MAX_BYTES = 2_000_000


def private_names(inventory_root: Path) -> set[str]:
    """Require every legacy inventory; never reveal its contents."""
    labels = inventory_root / "labels"
    if inventory_root.is_symlink() or labels.is_symlink():
        raise ValueError("inventory unavailable or unsafe")
    names: set[str] = set()
    for name in ("master_data.csv", "train_labels.csv", "val_labels.csv", "test_labels.csv"):
        path = labels / name
        if path.is_symlink() or not path.is_file():
            raise ValueError("inventory unavailable or unsafe")
        try:
            with path.open(encoding="utf-8", newline="") as handle:
                reader = csv.DictReader(handle)
                if not reader.fieldnames or "filename" not in reader.fieldnames:
                    raise ValueError("invalid inventory")
                for row in reader:
                    value = row.get("filename")
                    if not value or "/" in value or "\\" in value or value in {".", ".."}:
                        raise ValueError("invalid inventory")
                    names.add(value.casefold())
        except (OSError, UnicodeError, csv.Error) as exc:
            raise ValueError("inventory unavailable or unsafe") from exc
    if not names:
        raise ValueError("inventory empty")
    return names


def _safe_relative(path: str) -> bool:
    p = PurePosixPath(path)
    return bool(path) and not p.is_absolute() and "\\" not in path and all(part not in {".", ".."} for part in path.split("/"))


def scan(root: Path, inventory_root: Path, candidates: list[str] | None = None) -> list[str]:
    """Return redacted findings; every unknown file type fails closed."""
    findings: list[str] = []
    try:
        names = private_names(inventory_root)
    except ValueError:
        names = set()
        findings.append("private filename inventory unavailable; review blocked")
    if root.is_symlink() or not root.is_dir():
        return findings + ["release root unavailable or symlinked"]
    if candidates is None:
        candidates = []
        for base, dirs, files in os.walk(root, followlinks=False):
            base_path = Path(base)
            for directory in list(dirs):
                target = base_path / directory
                if target.is_symlink() or directory.casefold() in PRIVATE_DIRS:
                    findings.append("blocked directory or symlink detected")
                    dirs.remove(directory)
            candidates.extend((base_path / f).relative_to(root).as_posix() for f in files)
    for relative in candidates:
        if not _safe_relative(relative):
            findings.append("unsafe candidate path")
            continue
        parts = PurePosixPath(relative).parts
        path = root.joinpath(*parts)
        if any(part.casefold() in PRIVATE_DIRS for part in parts):
            findings.append("private candidate blocked")
            continue
        if any(root.joinpath(*parts[:i]).is_symlink() for i in range(1, len(parts) + 1)):
            findings.append("symlink candidate blocked")
            continue
        if not path.is_file():
            findings.append("missing or non-regular candidate")
            continue
        if any(name in relative.casefold() for name in names):
            findings.append("private filename in candidate path")
        suffix = path.suffix.lower()
        if suffix == ".ipynb":
            findings.append("unreviewed notebook blocked")
            try:
                if path.stat().st_size > MAX_BYTES:
                    raise ValueError("notebook too large")
                notebook = json.loads(path.read_text(encoding="utf-8"))
                if any(any(str(key).startswith("image/") for key in output.get("data", {})) for cell in notebook.get("cells", []) for output in cell.get("outputs", [])):
                    findings.append("embedded notebook image blocked")
            except (OSError, UnicodeError, ValueError, AttributeError, TypeError):
                findings.append("notebook could not be inspected")
            continue
        if suffix in BLOCKED_SUFFIXES or path.name.startswith(".env"):
            findings.append("sensitive or binary artifact blocked")
            continue
        if suffix not in TEXT_SUFFIXES and path.name != ".gitignore":
            findings.append("unknown file type blocked")
            continue
        try:
            if path.stat().st_size > MAX_BYTES:
                raise ValueError("file too large")
            content = path.read_text(encoding="utf-8")
            if "\x00" in content:
                raise ValueError("binary content")
        except (OSError, UnicodeError, ValueError):
            findings.append("candidate content could not be inspected")
            continue
        if LOCAL_PATH.search(content):
            findings.append("local absolute path detected")
        if SECRET.search(content):
            findings.append("possible secret detected")
        if any(name in content.casefold() for name in names):
            findings.append("private filename in candidate content")
    return findings


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=Path.cwd())
    parser.add_argument("--inventory-root", type=Path, help="private project containing labels/; defaults to root")
    parser.add_argument("--manifest", type=Path, help="UTF-8 list of candidate paths relative to root")
    args = parser.parse_args()
    try:
        candidates = args.manifest.read_text(encoding="utf-8").splitlines() if args.manifest else None
        findings = scan(args.root, args.inventory_root or args.root, candidates)
    except (OSError, UnicodeError):
        findings = ["candidate manifest unavailable"]
    for finding in sorted(set(findings)):
        print(f"BLOCKED: {finding}")
    print("Release screening blocked." if findings else "No automated findings; manual privacy and rights review still required.")
    return 1 if findings else 0


if __name__ == "__main__":
    raise SystemExit(main())
