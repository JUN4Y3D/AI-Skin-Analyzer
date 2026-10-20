import csv
import importlib.util
import sys
from pathlib import Path

import pytest
from PIL import Image, PngImagePlugin


MODULE_PATH = Path(__file__).resolve().parents[1] / "scripts" / "validate_dataset_recovery.py"
SPEC = importlib.util.spec_from_file_location("validate_dataset_recovery", MODULE_PATH)
recovery = importlib.util.module_from_spec(SPEC)
assert SPEC.loader is not None
sys.modules[SPEC.name] = recovery
SPEC.loader.exec_module(recovery)


def write_csv(path, rows):
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=recovery.REQUIRED_COLUMNS)
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
    for split in recovery.SPLITS:
        (tmp_path / split).mkdir()
    return tmp_path


def save_pattern(path, quality=None):
    image = Image.new("RGB", (16, 16))
    for x in range(16):
        for y in range(16):
            image.putpixel((x, y), (x * 12, y * 11, (x + y) * 6))
    kwargs = {"quality": quality} if quality is not None else {}
    image.save(path, **kwargs)


def test_exact_cross_split_group_and_known_label_conflict(tmp_path):
    project = make_project(tmp_path)
    train_a = project / "train" / "a.png"
    save_pattern(train_a)
    (project / "train" / "b.png").write_bytes(train_a.read_bytes())
    (project / "test" / "c.png").write_bytes(train_a.read_bytes())
    Image.new("RGB", (16, 16), "white").save(project / "val" / "v.png")

    rows = {
        "train": [row("a.png", age="20"), row("b.png", age="21")],
        "val": [row("v.png")],
        "test": [row("c.png", age="20")],
    }
    for split, split_rows in rows.items():
        write_csv(project / "labels" / f"{split}_labels.csv", split_rows)
    write_csv(project / "labels" / "master_data.csv", sum(rows.values(), []))

    summary, exact, perceptual = recovery.audit_dataset(project)
    assert summary["exact_duplicates"]["groups"] == 1
    assert summary["exact_duplicates"]["cross_split_groups"] == 1
    assert summary["exact_duplicates"]["conflicting_label_groups"] == 1
    assert len(exact) == 3
    assert {item["label_conflict_fields"] for item in exact} == {"skin_age"}
    assert perceptual == []


def test_perceptual_candidates_are_separate_and_unverified(tmp_path):
    project = make_project(tmp_path)
    source = project / "train" / "a.png"
    save_pattern(source)
    with Image.open(source) as image:
        metadata = PngImagePlugin.PngInfo()
        metadata.add_text("test-note", "different bytes, same pixels")
        image.save(project / "test" / "b.png", pnginfo=metadata)
    Image.new("RGB", (16, 16), "black").save(project / "val" / "v.png")
    rows = {
        "train": [row("a.png")],
        "val": [row("v.png")],
        "test": [row("b.png")],
    }
    for split, split_rows in rows.items():
        write_csv(project / "labels" / f"{split}_labels.csv", split_rows)
    write_csv(project / "labels" / "master_data.csv", sum(rows.values(), []))

    summary, exact, perceptual = recovery.audit_dataset(project, phash_threshold=4)
    assert exact == []
    assert summary["perceptual_similarity"]["cross_split_nonexact_candidates"] >= 1
    assert all(
        item["verification_status"] == "unverified_visual_similarity_candidate"
        and item["identity_inference"] == "not_performed"
        for item in perceptual
    )


def test_private_writer_refuses_overwrite_and_non_private_path(tmp_path):
    project = make_project(tmp_path)
    rows = [{"privacy_scope": recovery.PRIVATE_SCOPE, "value": "test"}]
    target = project / "reports" / "private" / "manifest.csv"
    recovery.write_new_private_csv(project, target, rows)
    with pytest.raises(FileExistsError):
        recovery.write_new_private_csv(project, target, rows)
    with pytest.raises(ValueError):
        recovery.write_new_private_csv(project, project / "labels" / "manifest.csv", rows)


def test_private_writer_refuses_symlinked_private_directory(tmp_path):
    project = make_project(tmp_path)
    outside = tmp_path / "elsewhere"
    outside.mkdir()
    (project / "reports").mkdir()
    (project / "reports" / "private").symlink_to(outside, target_is_directory=True)
    with pytest.raises(ValueError):
        recovery.write_new_private_csv(project, project / "reports" / "private" / "new.csv", [{"value": "test"}])
    assert list(outside.iterdir()) == []
