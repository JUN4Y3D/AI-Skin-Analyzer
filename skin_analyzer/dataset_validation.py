"""Read-only validation of the existing dataset and label manifests."""

from __future__ import annotations

import json
import platform
import sys
from collections import Counter
from pathlib import Path
from typing import Any
from importlib.metadata import PackageNotFoundError, version

from PIL import Image, UnidentifiedImageError

from .config import IMAGE_SIZE, REQUIRED_COLUMNS, SPLITS, SUPPORTED_EXTENSIONS
from .labels import LabelRecord, parse_label_csv, validate_record


def _record_dict(record: LabelRecord) -> dict[str, Any]:
    return {
        "filename": record.filename,
        "skin_type": record.skin_type,
        "has_acne": record.has_acne,
        "has_dark_circle": record.has_dark_circle,
        "skin_age": record.skin_age,
    }


def _image_checks(directory: Path) -> dict[str, Any]:
    if directory.is_symlink() or any(p.is_symlink() for p in directory.iterdir()):
        raise ValueError("symlinks in dataset directories are not supported")
    files = sorted(p for p in directory.iterdir() if p.is_file() and not p.name.startswith("."))
    extension_counts = Counter(p.suffix.lower() for p in files)
    unsupported = [p.name for p in files if p.suffix.lower() not in SUPPORTED_EXTENSIONS]
    empty = [p.name for p in files if p.stat().st_size == 0]
    unreadable: list[dict[str, str]] = []
    signatures = Counter()
    for path in files:
        if path.name in empty or path.suffix.lower() not in SUPPORTED_EXTENSIONS:
            continue
        try:
            with Image.open(path) as image:
                image.verify()
                signatures[image.format or "UNKNOWN"] += 1
        except (OSError, UnidentifiedImageError) as exc:
            unreadable.append({"filename": path.name, "error": str(exc)})
    return {
        "file_count": len(files),
        "extension_counts": dict(sorted(extension_counts.items())),
        "unsupported_extensions": unsupported,
        "empty_files": empty,
        "unreadable_files": unreadable,
        "image_signatures": dict(sorted(signatures.items())),
    }


def _label_counts(records: list[LabelRecord]) -> dict[str, dict[str, int]]:
    return {
        "skin_type": dict(sorted(Counter(r.skin_type for r in records).items())),
        "has_acne": dict(sorted(Counter(str(r.has_acne) for r in records).items())),
        "has_dark_circle": dict(
            sorted(Counter(str(r.has_dark_circle) for r in records).items())
        ),
        "skin_age": dict(sorted(Counter(str(r.skin_age) for r in records).items())),
    }


def validate_project(project_root: Path) -> dict[str, Any]:
    """Return a JSON-serializable report; never mutates project files."""
    labels_dir = project_root / "labels"
    if project_root.is_symlink() or labels_dir.is_symlink():
        raise ValueError("symlinked dataset root or labels directory is not supported")
    records_by_split: dict[str, list[LabelRecord]] = {}
    errors: list[str] = []
    warnings = [
        "Subject independence is unverified: no reliable subject identifiers were found."
    ]
    split_reports: dict[str, Any] = {}

    for split in SPLITS:
        csv_path = labels_dir / f"{split}_labels.csv"
        image_dir = project_root / split
        if csv_path.is_symlink() or image_dir.is_symlink():
            raise ValueError("symlinked dataset inputs are not supported")
        try:
            records = parse_label_csv(csv_path, REQUIRED_COLUMNS)
        except (OSError, ValueError) as exc:
            errors.append(str(exc))
            records = []
        records_by_split[split] = records
        filename_list = [r.filename for r in records]
        duplicates = sorted(
            filename for filename, count in Counter(filename_list).items() if count > 1
        )
        file_report = _image_checks(image_dir) if image_dir.is_dir() else {
            "file_count": 0,
            "extension_counts": {},
            "unsupported_extensions": [],
            "empty_files": [],
            "unreadable_files": [],
            "image_signatures": {},
        }
        actual_files = {
            p.name for p in image_dir.iterdir()
            if p.is_file() and not p.name.startswith(".")
        } if image_dir.is_dir() else set()
        missing_files = sorted(set(filename_list) - actual_files)
        unlabeled_files = sorted(actual_files - set(filename_list))
        invalid_labels = []
        for record in records:
            for issue in validate_record(record):
                invalid_labels.append({"filename": record.filename, "issue": issue})
        for filename in duplicates:
            errors.append(f"{split}: duplicate filename {filename!r}")
        errors.extend(f"{split}: missing image {name!r}" for name in missing_files)
        errors.extend(f"{split}: unlabeled image {name!r}" for name in unlabeled_files)
        errors.extend(
            f"{split}: {item['filename']}: {item['issue']}" for item in invalid_labels
        )
        if file_report["unsupported_extensions"]:
            errors.append(f"{split}: unsupported image extensions found")
        if file_report["empty_files"] or file_report["unreadable_files"]:
            errors.append(f"{split}: empty or unreadable image files found")
        split_reports[split] = {
            "csv_rows": len(records),
            "image_files": file_report["file_count"],
            "duplicate_filenames": duplicates,
            "missing_image_files": missing_files,
            "unlabeled_image_files": unlabeled_files,
            "invalid_labels": invalid_labels,
            "label_counts": _label_counts(records),
            "image_checks": file_report,
        }

    filename_sets = {
        split: {record.filename for record in records}
        for split, records in records_by_split.items()
    }
    overlaps: dict[str, list[str]] = {}
    for index, first in enumerate(SPLITS):
        for second in SPLITS[index + 1 :]:
            overlaps[f"{first}/{second}"] = sorted(
                filename_sets[first] & filename_sets[second]
            )
            if overlaps[f"{first}/{second}"]:
                errors.append(f"cross-split filename overlap: {first}/{second}")

    master_path = labels_dir / "master_data.csv"
    if master_path.is_symlink():
        raise ValueError("symlinked dataset inputs are not supported")
    try:
        master_records = parse_label_csv(master_path, REQUIRED_COLUMNS)
    except (OSError, ValueError) as exc:
        errors.append(str(exc))
        master_records = []
    master_by_filename = {record.filename: record for record in master_records}
    master_duplicates = sorted(
        filename
        for filename, count in Counter(record.filename for record in master_records).items()
        if count > 1
    )
    if master_duplicates:
        errors.append("master: duplicate filenames found")
    union_by_filename = {
        record.filename: record
        for records in records_by_split.values()
        for record in records
    }
    master_not_in_splits = sorted(set(master_by_filename) - set(union_by_filename))
    splits_not_in_master = sorted(set(union_by_filename) - set(master_by_filename))
    mismatches = []
    for filename in sorted(set(master_by_filename) & set(union_by_filename)):
        if master_by_filename[filename] != union_by_filename[filename]:
            mismatches.append(
                {
                    "filename": filename,
                    "master": _record_dict(master_by_filename[filename]),
                    "split": _record_dict(union_by_filename[filename]),
                }
            )
    errors.extend(f"master filename absent from splits: {name!r}" for name in master_not_in_splits)
    errors.extend(f"split filename absent from master: {name!r}" for name in splits_not_in_master)
    if mismatches:
        errors.append("master/split label mismatches found")

    dependency_versions: dict[str, str] = {}
    for package in ("numpy", "Pillow", "pytest"):
        try:
            dependency_versions[package] = version(package)
        except PackageNotFoundError:
            dependency_versions[package] = "not-installed"

    return {
        "project_root": str(project_root.resolve()),
        "python_version": platform.python_version(),
        "implementation": sys.implementation.name,
        "dependency_versions": dependency_versions,
        "configuration": {
            "image_size": list(IMAGE_SIZE),
            "supported_extensions": sorted(SUPPORTED_EXTENSIONS),
            "preprocessing": "Keras ResNet50 ImageNet caffe-mode equivalent",
        },
        "subject_independence": {
            "status": "unverified",
            "reason": "No reliable subject identifiers or identity metadata are available.",
        },
        "splits": split_reports,
        "cross_split_filename_overlap": overlaps,
        "master": {
            "csv_rows": len(master_records),
            "duplicate_filenames": master_duplicates,
            "label_counts": _label_counts(master_records),
        },
        "master_split_reconciliation": {
            "master_not_in_splits": master_not_in_splits,
            "splits_not_in_master": splits_not_in_master,
            "label_mismatches": mismatches,
        },
        "errors": errors,
        "warnings": warnings,
        "status": "failed" if errors else "passed_with_warnings",
    }


def write_report(report: dict[str, Any], output_dir: Path, allow_overwrite: bool = False) -> tuple[Path, Path]:
    """Write JSON and Markdown reports, refusing accidental overwrite."""
    output_dir.mkdir(parents=True, exist_ok=True)
    json_path = output_dir / "dataset_validation.json"
    markdown_path = output_dir / "dataset_validation.md"
    if not allow_overwrite and (json_path.exists() or markdown_path.exists()):
        raise FileExistsError(
            f"validation reports already exist in {output_dir}; use --force to overwrite"
        )
    json_path.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    lines = [
        "# Dataset Validation Report",
        "",
        f"Status: **{report['status']}**",
        f"Project root: `{report['project_root']}`",
        f"Python: `{report['python_version']}` ({report['implementation']})",
        "Subject independence: **unverified**",
        "",
        "## Split summary",
        "",
        "| Split | CSV rows | Image files | Missing labels | Unlabelled files |",
        "|---|---:|---:|---:|---:|",
    ]
    for split, details in report["splits"].items():
        lines.append(
            f"| {split} | {details['csv_rows']} | {details['image_files']} | "
            f"{len(details['missing_image_files'])} | {len(details['unlabeled_image_files'])} |"
        )
    lines.extend(["", "## Errors", ""])
    if report["errors"]:
        lines.extend(f"- {error}" for error in report["errors"])
    else:
        lines.append("- None")
    lines.extend(["", "## Warnings", ""])
    lines.extend(f"- {warning}" for warning in report["warnings"])
    markdown_path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return json_path, markdown_path
