"""Non-destructive dataset recovery validation and private manifest generation.

The validator never edits image or label files. Optional CSV outputs are limited
to ``reports/private`` and are created only when the target does not exist.
No identity inference or face recognition is performed.
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import math
from collections import Counter, defaultdict
from dataclasses import dataclass
from itertools import combinations
from pathlib import Path
from typing import Any, Iterable

import numpy as np
from PIL import Image


SPLITS = ("train", "val", "test")
REQUIRED_COLUMNS = (
    "filename",
    "skin_type",
    "has_acne",
    "has_dark_circle",
    "skin_age",
)
MISSING_VALUES = {
    "skin_type": "Unknown",
    "has_acne": "-1",
    "has_dark_circle": "-1",
    "skin_age": "-1",
}
PRIVATE_SCOPE = "PRIVATE_LOCAL_REVIEW_DO_NOT_COMMIT"
SUPPORTED_EXTENSIONS = {".jpg", ".jpeg", ".png"}


@dataclass(frozen=True)
class Entry:
    split: str
    filename: str
    relative_path: str
    sha256: str
    phash: int
    labels: dict[str, str]


def read_labels(path: Path) -> list[dict[str, str]]:
    """Read a strict label CSV without modifying it."""
    if path.is_symlink() or path.parent.is_symlink():
        raise ValueError("symlinked labels are not supported")
    with path.open("r", encoding="utf-8", newline="") as handle:
        reader = csv.DictReader(handle)
        if tuple(reader.fieldnames or ()) != REQUIRED_COLUMNS:
            raise ValueError(f"unexpected schema in {path.name}")
        rows = list(reader)
    names = [row["filename"] for row in rows]
    if len(names) != len(set(names)):
        raise ValueError(f"duplicate filename rows in {path.name}")
    for name in names:
        candidate = Path(name)
        if not name or name in {".", ".."} or "\\" in name or candidate.is_absolute() or candidate.name != name or ".." in candidate.parts:
            raise ValueError(f"unsafe filename in {path.name}")
    return rows


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _dct_matrix(size: int = 32) -> np.ndarray:
    matrix = np.zeros((size, size), dtype=np.float64)
    for frequency in range(size):
        scale = math.sqrt(1 / size) if frequency == 0 else math.sqrt(2 / size)
        for position in range(size):
            matrix[frequency, position] = scale * math.cos(
                math.pi * (2 * position + 1) * frequency / (2 * size)
            )
    return matrix


_DCT_32 = _dct_matrix()


def perceptual_hash(image: Image.Image) -> int:
    """Return a deterministic 64-bit pHash; it is not an identity signal."""
    pixels = np.asarray(
        image.convert("L").resize((32, 32), Image.Resampling.LANCZOS),
        dtype=np.float64,
    )
    transformed = _DCT_32 @ pixels @ _DCT_32.T
    block = transformed[:8, :8]
    median = np.median(block.reshape(-1)[1:])
    value = 0
    for bit in (block > median).reshape(-1):
        value = (value << 1) | int(bit)
    return value


def _known_conflict_fields(entries: Iterable[Entry]) -> list[str]:
    entries = list(entries)
    conflicts: list[str] = []
    for field, missing in MISSING_VALUES.items():
        values = {entry.labels[field] for entry in entries if entry.labels[field] != missing}
        if len(values) > 1:
            conflicts.append(field)
    return conflicts


def _label_summary(rows: list[dict[str, str]]) -> dict[str, dict[str, int]]:
    return {
        field: dict(sorted(Counter(row[field] for row in rows).items()))
        for field in REQUIRED_COLUMNS[1:]
    }


def audit_dataset(
    project_root: Path, phash_threshold: int = 4
) -> tuple[dict[str, Any], list[dict[str, Any]], list[dict[str, Any]]]:
    """Audit split integrity and return summary plus two private manifest tables."""
    if project_root.is_symlink():
        raise ValueError("symlinked project root is not supported")
    project_root = project_root.resolve()
    rows_by_split: dict[str, list[dict[str, str]]] = {}
    all_rows: list[dict[str, str]] = []
    entries: list[Entry] = []
    reconciliation: dict[str, dict[str, int]] = {}
    formats: Counter[str] = Counter()
    modes: Counter[str] = Counter()
    dimensions: Counter[str] = Counter()

    for split in SPLITS:
        rows = read_labels(project_root / "labels" / f"{split}_labels.csv")
        rows_by_split[split] = rows
        all_rows.extend(rows)
        by_name = {row["filename"]: row for row in rows}
        directory = project_root / split
        if directory.is_symlink() or any(path.is_symlink() for path in directory.iterdir()):
            raise ValueError("symlinked images or split directories are not supported")
        files = sorted(
            path for path in directory.iterdir() if path.is_file() and not path.name.startswith(".")
        )
        file_names = {path.name for path in files}
        csv_names = set(by_name)
        reconciliation[split] = {
            "csv_rows": len(rows),
            "image_files": len(files),
            "missing_references": len(csv_names - file_names),
            "unlabelled_files": len(file_names - csv_names),
        }
        for path in files:
            if path.suffix.lower() not in SUPPORTED_EXTENSIONS:
                continue
            with Image.open(path) as image:
                image.load()
                formats[image.format or "UNKNOWN"] += 1
                modes[image.mode] += 1
                dimensions[f"{image.width}x{image.height}"] += 1
                image_phash = perceptual_hash(image)
            row = by_name.get(path.name)
            if row is None:
                continue
            entries.append(
                Entry(
                    split=split,
                    filename=path.name,
                    relative_path=f"{split}/{path.name}",
                    sha256=sha256_file(path),
                    phash=image_phash,
                    labels={field: row[field] for field in REQUIRED_COLUMNS[1:]},
                )
            )

    master_rows = read_labels(project_root / "labels" / "master_data.csv")
    master_by_name = {
        row["filename"]: tuple(row[field] for field in REQUIRED_COLUMNS[1:])
        for row in master_rows
    }
    split_by_name = {
        row["filename"]: tuple(row[field] for field in REQUIRED_COLUMNS[1:])
        for row in all_rows
    }

    by_sha: dict[str, list[Entry]] = defaultdict(list)
    for entry in entries:
        by_sha[entry.sha256].append(entry)
    duplicate_groups = [group for group in by_sha.values() if len(group) > 1]
    duplicate_groups.sort(key=lambda group: group[0].sha256)

    exact_manifest: list[dict[str, Any]] = []
    cross_split_exact_groups = 0
    conflicting_exact_groups = 0
    for index, group in enumerate(duplicate_groups, start=1):
        group_id = f"exact-{index:04d}"
        splits = sorted({entry.split for entry in group})
        conflicts = _known_conflict_fields(group)
        if len(splits) > 1:
            cross_split_exact_groups += 1
        if conflicts:
            conflicting_exact_groups += 1
        for entry in sorted(group, key=lambda item: (item.split, item.relative_path)):
            exact_manifest.append(
                {
                    "privacy_scope": PRIVATE_SCOPE,
                    "group_id": group_id,
                    "verification_status": "verified_exact_sha256",
                    "cross_split": str(len(splits) > 1).lower(),
                    "group_splits": "|".join(splits),
                    "label_conflict_fields": "|".join(conflicts),
                    "sha256": entry.sha256,
                    "split": entry.split,
                    "relative_path": entry.relative_path,
                    **entry.labels,
                }
            )

    entries_by_split = {
        split: [entry for entry in entries if entry.split == split] for split in SPLITS
    }
    perceptual_manifest: list[dict[str, Any]] = []
    candidate_index = 1
    for first, second in combinations(SPLITS, 2):
        for left in entries_by_split[first]:
            for right in entries_by_split[second]:
                if left.sha256 == right.sha256:
                    continue
                distance = (left.phash ^ right.phash).bit_count()
                if distance <= phash_threshold:
                    perceptual_manifest.append(
                        {
                            "privacy_scope": PRIVATE_SCOPE,
                            "candidate_id": f"phash-{candidate_index:05d}",
                            "verification_status": "unverified_visual_similarity_candidate",
                            "identity_inference": "not_performed",
                            "phash_hamming_distance": distance,
                            "split_a": left.split,
                            "relative_path_a": left.relative_path,
                            "sha256_a": left.sha256,
                            "split_b": right.split,
                            "relative_path_b": right.relative_path,
                            "sha256_b": right.sha256,
                        }
                    )
                    candidate_index += 1

    summary = {
        "policy": {
            "dataset_mutated": False,
            "identity_inference_performed": False,
            "perceptual_candidates_are_verified_duplicates": False,
        },
        "reconciliation": reconciliation,
        "master": {
            "rows": len(master_rows),
            "master_only": len(set(master_by_name) - set(split_by_name)),
            "splits_only": len(set(split_by_name) - set(master_by_name)),
            "label_mismatches": sum(
                master_by_name[name] != split_by_name[name]
                for name in set(master_by_name) & set(split_by_name)
            ),
        },
        "labels": _label_summary(master_rows),
        "images": {
            "audited": len(entries),
            "formats": dict(sorted(formats.items())),
            "modes": dict(sorted(modes.items())),
            "dimensions": dict(sorted(dimensions.items())),
        },
        "exact_duplicates": {
            "groups": len(duplicate_groups),
            "files_in_groups": sum(len(group) for group in duplicate_groups),
            "cross_split_groups": cross_split_exact_groups,
            "conflicting_label_groups": conflicting_exact_groups,
        },
        "perceptual_similarity": {
            "algorithm": "64-bit pHash (32x32 DCT, top-left 8x8)",
            "threshold": phash_threshold,
            "cross_split_nonexact_candidates": len(perceptual_manifest),
            "status": "unverified; not an identity signal",
        },
    }
    return summary, exact_manifest, perceptual_manifest


def write_new_private_csv(project_root: Path, path: Path, rows: list[dict[str, Any]]) -> None:
    """Write a new private report CSV, refusing overwrite or dataset locations."""
    if project_root.is_symlink() or (project_root / "reports").is_symlink() or (project_root / "reports" / "private").is_symlink() or path.is_symlink():
        raise ValueError("symlinked private report paths are not supported")
    project_root = project_root.resolve()
    target = path.resolve()
    private_root = (project_root / "reports" / "private").resolve()
    if target.parent != private_root or target.suffix.lower() != ".csv":
        raise ValueError("private manifests must be CSV files directly under reports/private")
    if target.exists():
        raise FileExistsError(f"refusing to overwrite existing private manifest: {target.name}")
    target.parent.mkdir(parents=True, exist_ok=True)
    if not rows:
        raise ValueError("refusing to write an empty private manifest")
    with target.open("x", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Read-only audit of AI Skin Analyzer split integrity and duplicates."
    )
    parser.add_argument("--project-root", type=Path, default=Path.cwd())
    parser.add_argument("--phash-threshold", type=int, default=4)
    parser.add_argument("--exact-manifest", type=Path)
    parser.add_argument("--perceptual-manifest", type=Path)
    args = parser.parse_args(argv)
    if (args.exact_manifest is None) != (args.perceptual_manifest is None):
        parser.error("provide both private manifest paths or neither")
    if not 0 <= args.phash_threshold <= 16:
        parser.error("phash threshold must be between 0 and 16")

    summary, exact_rows, perceptual_rows = audit_dataset(
        args.project_root, phash_threshold=args.phash_threshold
    )
    if args.exact_manifest is not None and args.perceptual_manifest is not None:
        write_new_private_csv(args.project_root, args.exact_manifest, exact_rows)
        write_new_private_csv(args.project_root, args.perceptual_manifest, perceptual_rows)
        summary["private_manifests"] = {
            "exact_rows": len(exact_rows),
            "perceptual_rows": len(perceptual_rows),
            "privacy_scope": PRIVATE_SCOPE,
        }
    print(json.dumps(summary, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
