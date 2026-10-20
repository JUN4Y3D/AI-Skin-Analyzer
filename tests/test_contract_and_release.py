import csv
import json

import pytest

from skin_analyzer.config import REQUIRED_COLUMNS
from skin_analyzer.dataset_validation import _image_checks
from skin_analyzer.labels import LabelRecord, SKIN_TYPE_TO_CLASS, task_arrays, validate_record
from skin_analyzer.model_contract import INPUT_SHAPE, MODEL_CONTRACT_VERSION, OUTPUTS, SKIN_TYPE_CLASSES
from skin_analyzer.release_safety import scan


def inventory(root):
    labels = root / "labels"
    labels.mkdir()
    for name in ("master_data.csv", "train_labels.csv", "val_labels.csv", "test_labels.csv"):
        with (labels / name).open("w", newline="", encoding="utf-8") as handle:
            writer = csv.DictWriter(handle, fieldnames=REQUIRED_COLUMNS)
            writer.writeheader()
            writer.writerow(dict(zip(REQUIRED_COLUMNS, ["private-synthetic.jpg", "Unknown", -1, -1, -1])))


def test_model_metadata_agrees_with_label_schema():
    assert MODEL_CONTRACT_VERSION == "1.0.0"
    assert INPUT_SHAPE == (224, 224, 3)
    assert tuple(SKIN_TYPE_TO_CLASS) == SKIN_TYPE_CLASSES
    assert [o.name for o in OUTPUTS] == ["skin_type", "has_acne", "has_dark_circle", "skin_age"]
    assert [o.units for o in OUTPUTS] == [3, 1, 1, 1]
    assert all(o.status.startswith("unavailable") for o in OUTPUTS)


def test_negative_is_valid_and_distinct_from_missing():
    records = [LabelRecord("a.jpg", "Normal", 0, -1, -1), LabelRecord("b.jpg", "Unknown", -1, 1, 20)]
    assert not validate_record(records[0])
    assert task_arrays(records)["has_acne"] == ([0, -1], [True, False])


@pytest.mark.parametrize("name", ["../image.jpg", "dir/image.jpg", r"dir\image.jpg", "..", ""])
def test_reject_unsafe_filenames(name):
    assert validate_record(LabelRecord(name, "Normal", 0, 1, 20))


def test_dataset_check_rejects_symlink(tmp_path):
    directory = tmp_path / "train"
    directory.mkdir()
    (directory / "link.jpg").symlink_to(tmp_path / "outside.jpg")
    with pytest.raises(ValueError):
        _image_checks(directory)


def test_release_fails_closed_and_redacts(tmp_path):
    inventory(tmp_path)
    (tmp_path / "safe.md").write_text("safe text", encoding="utf-8")
    assert scan(tmp_path, tmp_path, ["safe.md"]) == []
    (tmp_path / "unsafe.md").write_text("private-synthetic.jpg", encoding="utf-8")
    findings = scan(tmp_path, tmp_path, ["unsafe.md", "../escape", "labels/master_data.csv"])
    assert "private filename in candidate content" in findings
    assert "unsafe candidate path" in findings
    assert "private candidate blocked" in findings
    assert "private-synthetic" not in " ".join(findings)


def test_release_blocks_missing_inventory_symlink_notebook_and_unknown(tmp_path):
    (tmp_path / "safe.md").write_text("hello", encoding="utf-8")
    assert scan(tmp_path, tmp_path, ["safe.md"])
    inventory(tmp_path)
    (tmp_path / "link.md").symlink_to(tmp_path / "safe.md")
    (tmp_path / "unknown.bin").write_bytes(b"x")
    (tmp_path / "notebook.ipynb").write_text(json.dumps({"cells": [{"outputs": [{"data": {"image/png": "abc"}}]}]}), encoding="utf-8")
    findings = scan(tmp_path, tmp_path, ["link.md", "unknown.bin", "notebook.ipynb"])
    assert "symlink candidate blocked" in findings
    assert "unknown file type blocked" in findings
    assert "embedded notebook image blocked" in findings


def test_release_blocks_local_path_and_secret(tmp_path):
    inventory(tmp_path)
    (tmp_path / "unsafe.md").write_text("/" + "Users/example/private\n" + "AKIA" + "A" * 16, encoding="utf-8")
    findings = scan(tmp_path, tmp_path, ["unsafe.md"])
    assert "local absolute path detected" in findings
    assert "possible secret detected" in findings


def test_release_allows_relative_private_documentation_and_web_source(tmp_path):
    inventory(tmp_path)
    (tmp_path / "app.js").write_text("const location = 'reports/private/artifacts';", encoding="utf-8")
    (tmp_path / "styles.css").write_text("body { color: white; }", encoding="utf-8")
    assert scan(tmp_path, tmp_path, ["app.js", "styles.css"]) == []


def test_release_blocks_windows_paths(tmp_path):
    inventory(tmp_path)
    (tmp_path / "unsafe.md").write_text("C:" + chr(92) + "private", encoding="utf-8")
    assert "local absolute path detected" in scan(tmp_path, tmp_path, ["unsafe.md"])
