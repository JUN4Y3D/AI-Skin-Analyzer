from skin_analyzer.labels import LabelRecord, skin_type_labels, task_arrays, validate_record


def test_skin_type_mapping_and_unknown_mask():
    labels, mask = skin_type_labels(["Normal", "Dry", "Oily", "Unknown"])
    assert labels == [0, 1, 2, -1]
    assert mask == [True, True, True, False]


def test_missing_binary_and_age_labels_are_masked():
    record = LabelRecord("image.jpg", "Unknown", -1, -1, -1)
    arrays = task_arrays([record])
    assert arrays["has_acne"] == ([-1], [False])
    assert arrays["has_dark_circle"] == ([-1], [False])
    assert arrays["skin_age"] == ([-1], [False])


def test_empty_valid_label_batch_has_all_false_masks():
    arrays = task_arrays(
        [LabelRecord("a.jpg", "Unknown", -1, -1, -1), LabelRecord("b.jpg", "Unknown", -1, -1, -1)]
    )
    assert all(not value for _, mask in arrays.values() for value in mask)


def test_invalid_label_domains_are_reported():
    errors = validate_record(LabelRecord("bad.jpg", "Fitzpatrick", 2, 2, 51))
    assert "invalid skin_type" in errors[0]
    assert any("has_acne" in error for error in errors)
    assert any("has_dark_circle" in error for error in errors)
    assert any("skin_age" in error for error in errors)
