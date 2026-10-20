import csv
import json

from PIL import Image

from skin_analyzer.dataset_validation import validate_project, write_report


def write_csv(path, rows):
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(
            handle,
            fieldnames=["filename", "skin_type", "has_acne", "has_dark_circle", "skin_age"],
        )
        writer.writeheader()
        writer.writerows(rows)


def row(filename, skin="Normal", acne="1", dark="1", age="20"):
    return {
        "filename": filename,
        "skin_type": skin,
        "has_acne": acne,
        "has_dark_circle": dark,
        "skin_age": age,
    }


def make_project(tmp_path):
    (tmp_path / "labels").mkdir()
    for split in ("train", "val", "test"):
        (tmp_path / split).mkdir()
        write_csv(tmp_path / "labels" / f"{split}_labels.csv", [])
    return tmp_path


def test_quoted_filename_and_counts_reconcile(tmp_path):
    project = make_project(tmp_path)
    records = [row(f"face, {split}.png") for split in ("train", "val", "test")]
    for split, record in zip(("train", "val", "test"), records):
        write_csv(project / "labels" / f"{split}_labels.csv", [record])
        Image.new("RGB", (2, 2), "white").save(project / split / record["filename"])
    write_csv(project / "labels" / "master_data.csv", records)
    report = validate_project(project)
    assert report["errors"] == []
    assert report["master"]["csv_rows"] == 3
    assert report["splits"]["train"]["csv_rows"] == 1


def test_missing_and_unlabelled_files_are_structural_errors(tmp_path):
    project = make_project(tmp_path)
    record = row("missing.jpg")
    write_csv(project / "labels" / "train_labels.csv", [record])
    Image.new("RGB", (2, 2), "white").save(project / "train" / "extra.jpg")
    write_csv(project / "labels" / "master_data.csv", [record])
    report = validate_project(project)
    assert "missing.jpg" in report["splits"]["train"]["missing_image_files"]
    assert "extra.jpg" in report["splits"]["train"]["unlabeled_image_files"]
    assert report["status"] == "failed"


def test_cross_split_overlap_and_invalid_domain_are_detected(tmp_path):
    project = make_project(tmp_path)
    shared = row("shared.jpg", skin="Bad", acne="0")
    for split in ("train", "val"):
        write_csv(project / "labels" / f"{split}_labels.csv", [shared])
        Image.new("RGB", (2, 2), "white").save(project / split / "shared.jpg")
    write_csv(project / "labels" / "master_data.csv", [shared])
    report = validate_project(project)
    assert report["cross_split_filename_overlap"]["train/val"] == ["shared.jpg"]
    assert report["splits"]["train"]["invalid_labels"]


def test_report_refuses_overwrite(tmp_path):
    project = make_project(tmp_path)
    write_csv(project / "labels" / "master_data.csv", [])
    report = validate_project(project)
    output = tmp_path / "reports"
    write_report(report, output)
    try:
        write_report(report, output)
    except FileExistsError:
        pass
    else:
        raise AssertionError("expected report overwrite refusal")
    assert json.loads((output / "dataset_validation.json").read_text())["status"] == "passed_with_warnings"
