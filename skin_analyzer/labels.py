"""CSV label parsing and explicit missing-label semantics."""

from __future__ import annotations

import csv
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable, Mapping

SKIN_TYPE_TO_CLASS = {"Normal": 0, "Dry": 1, "Oily": 2}
VALID_SKIN_TYPES = frozenset((*SKIN_TYPE_TO_CLASS, "Unknown"))
VALID_BINARY_LABELS = frozenset({-1, 0, 1})
MIN_AGE = 15
MAX_AGE = 50


@dataclass(frozen=True)
class LabelRecord:
    filename: str
    skin_type: str
    has_acne: int
    has_dark_circle: int
    skin_age: int


def _parse_int(value: str, field: str, line_number: int) -> int:
    try:
        return int(value)
    except (TypeError, ValueError) as exc:
        raise ValueError(
            f"Line {line_number}: {field} must be an integer, got {value!r}"
        ) from exc


def parse_label_csv(path: Path, required_columns: Iterable[str]) -> list[LabelRecord]:
    """Parse a label CSV without splitting quoted filenames on commas."""
    required = tuple(required_columns)
    records: list[LabelRecord] = []
    with path.open("r", encoding="utf-8", newline="") as handle:
        reader = csv.DictReader(handle)
        if reader.fieldnames is None:
            raise ValueError(f"{path}: missing CSV header")
        if tuple(reader.fieldnames) != required:
            raise ValueError(
                f"{path}: expected columns {required!r}, got {reader.fieldnames!r}"
            )
        for line_number, row in enumerate(reader, start=2):
            if None in row or any(value is None for value in row.values()):
                raise ValueError(f"{path}: malformed row at line {line_number}")
            records.append(
                LabelRecord(
                    filename=row["filename"],
                    skin_type=row["skin_type"],
                    has_acne=_parse_int(row["has_acne"], "has_acne", line_number),
                    has_dark_circle=_parse_int(
                        row["has_dark_circle"], "has_dark_circle", line_number
                    ),
                    skin_age=_parse_int(row["skin_age"], "skin_age", line_number),
                )
            )
    return records


def validate_record(record: LabelRecord) -> list[str]:
    """Return domain errors for one record; missing labels are valid."""
    errors: list[str] = []
    if record.skin_type not in VALID_SKIN_TYPES:
        errors.append(f"invalid skin_type {record.skin_type!r}")
    if record.has_acne not in VALID_BINARY_LABELS:
        errors.append(f"invalid has_acne {record.has_acne!r}")
    if record.has_dark_circle not in VALID_BINARY_LABELS:
        errors.append(f"invalid has_dark_circle {record.has_dark_circle!r}")
    if record.skin_age != -1 and not MIN_AGE <= record.skin_age <= MAX_AGE:
        errors.append(f"invalid skin_age {record.skin_age!r}")
    if (not record.filename or record.filename in {".", ".."}
            or "/" in record.filename or "\\" in record.filename
            or any(ord(char) < 32 for char in record.filename)):
        errors.append("filename must be a safe single path component")
    return errors


def skin_type_labels(values: Iterable[str]) -> tuple[list[int], list[bool]]:
    """Map skin types and return labels plus a valid-label mask."""
    labels: list[int] = []
    mask: list[bool] = []
    for value in values:
        valid = value in SKIN_TYPE_TO_CLASS
        labels.append(SKIN_TYPE_TO_CLASS.get(value, -1))
        mask.append(valid)
    return labels, mask


def valid_label_mask(values: Iterable[int], missing_value: int = -1) -> list[bool]:
    """Return a boolean mask without treating missing labels as negatives."""
    return [value != missing_value for value in values]


def task_arrays(records: Iterable[LabelRecord]) -> Mapping[str, tuple[list[int], list[bool]]]:
    """Return task labels and masks with one-dimensional, aligned shapes."""
    records = list(records)
    skin_labels, skin_mask = skin_type_labels(r.skin_type for r in records)
    return {
        "skin_type": (skin_labels, skin_mask),
        "has_acne": (
            [r.has_acne for r in records],
            valid_label_mask((r.has_acne for r in records)),
        ),
        "has_dark_circle": (
            [r.has_dark_circle for r in records],
            valid_label_mask((r.has_dark_circle for r in records)),
        ),
        "skin_age": (
            [r.skin_age for r in records],
            valid_label_mask((r.skin_age for r in records)),
        ),
    }
