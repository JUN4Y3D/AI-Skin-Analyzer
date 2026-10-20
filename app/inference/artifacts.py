"""Private artifact validation copied from the verified Phase 6N contract."""
from __future__ import annotations

import hashlib
import json
import os
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import numpy as np


RUNS = Path("reports/private/phase6_training_runs")
CLASSES = ("Dry", "Normal", "Oily")
PREPROCESSING = "tf.keras.applications.resnet50.preprocess_input on RGB float32 0..255"


@dataclass(frozen=True)
class ArtifactBundle:
    model_path: Path
    skin_metrics: dict[str, Any]
    component_metrics: dict[str, Any]
    age: dict[str, np.ndarray]
    references: dict[str, dict[str, np.ndarray]]


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _regular_file(path: Path, label: str) -> Path:
    if path.is_symlink() or not path.is_file():
        raise ValueError(f"Missing or unsafe local {label}")
    return path


def _run_directory(project_root: Path, run_name: str, prefix: str) -> Path:
    parent = project_root / RUNS
    if parent.is_symlink() or not parent.is_dir():
        raise ValueError("Missing or unsafe private training directory")
    if not run_name.startswith(prefix) or any(token in run_name for token in ("/", "\\", "..")):
        raise ValueError("Unexpected model run name")
    path = parent / run_name
    if path.is_symlink() or not path.is_dir():
        raise ValueError("Missing or unsafe model run")
    if path.resolve(strict=True).parent != parent.resolve(strict=True):
        raise ValueError("Model run resolves outside the private training directory")
    return path


def _npz(path: Path, keys: set[str]) -> dict[str, np.ndarray]:
    _regular_file(path, path.name)
    with np.load(path, allow_pickle=False) as stored:
        if set(stored.files) != keys:
            raise ValueError(f"Unexpected arrays in {path.name}")
        arrays = {key: stored[key].copy() for key in stored.files}
    if not all(np.issubdtype(value.dtype, np.number) and np.isfinite(value).all() for value in arrays.values()):
        raise ValueError(f"Nonfinite or nonnumeric values in {path.name}")
    return arrays


def load_artifacts(project_root: Path, skin_run: str, components_run: str) -> ArtifactBundle:
    """Validate and load only the fitted artifact arrays required for inference."""
    root = project_root.resolve(strict=True)
    skin_dir = _run_directory(root, skin_run, "skin_type_phase6k_finetune_")
    component_dir = _run_directory(root, components_run, "phase6l_other_components_")
    model = _regular_file(skin_dir / "best_development_model.keras", "Phase 6K checkpoint")
    skin_metrics_path = _regular_file(skin_dir / "development_metrics.json", "Phase 6K metrics")
    component_metrics_path = _regular_file(component_dir / "prototype_metrics.json", "Phase 6L metrics")
    skin_metrics = json.loads(skin_metrics_path.read_text(encoding="utf-8"))
    component_metrics = json.loads(component_metrics_path.read_text(encoding="utf-8"))

    if (
        skin_metrics.get("status") != "PHASE6K_EXPLORATORY_FINE_TUNED_NOT_INDEPENDENT_HOLDOUT"
        or skin_metrics.get("training_classes_order") != list(CLASSES)
        or skin_metrics.get("input_preprocessing") != PREPROCESSING
    ):
        raise ValueError("Unsupported skin-type checkpoint metadata")
    if component_metrics.get("status") != "PHASE6L_PROTOTYPE_UNVALIDATED_TASKS":
        raise ValueError("Unsupported Phase 6L component status")
    if component_metrics.get("input_source_model") != str(model.relative_to(root)):
        raise ValueError("Phase 6L references a different skin-type model")
    if component_metrics.get("input_model_sha256") != sha256(model):
        raise ValueError("Phase 6K model changed since Phase 6L fitting")
    if component_metrics.get("input_metrics_sha256") != sha256(skin_metrics_path):
        raise ValueError("Phase 6K metrics changed since Phase 6L fitting")

    provenance = (
        ("reports/private/phase6d_review_purged_skin_type_manifest.csv", "manifest_sha256", "input_manifest_sha256"),
        ("reports/private/phase6c_candidate_derivative_review.csv", "review_csv_sha256", "input_review_sha256"),
    )
    attestations = None
    for relative, skin_key, component_key in provenance:
        source = root / relative
        if source.is_file() and not source.is_symlink():
            actual = sha256(_regular_file(source, "private provenance file"))
        elif (
            os.environ.get("AI_SKIN_HOSTED_INFERENCE") == "1"
            or (root / "reports/private/hosted_provenance_sha256.json").is_file()
        ):
            if attestations is None:
                proof = _regular_file(root / "reports/private/hosted_provenance_sha256.json", "hosted provenance attestation")
                attestations = json.loads(proof.read_text(encoding="utf-8"))
                if not isinstance(attestations, dict) or set(attestations) != {entry[0] for entry in provenance}:
                    raise ValueError("Invalid hosted provenance attestation")
            actual = attestations.get(relative)
            if not isinstance(actual, str) or len(actual) != 64:
                raise ValueError("Invalid hosted provenance digest")
        else:
            raise ValueError("Missing or unsafe private provenance file")
        if actual != skin_metrics.get(skin_key) or actual != component_metrics.get(component_key):
            raise ValueError("Dataset provenance changed since model fitting")

    age = _npz(
        component_dir / "age_like_ridge.npz",
        {"support", "dual", "intercept", "alpha", "age_label_min", "age_label_max"},
    )
    references = {
        name: _npz(
            component_dir / f"{name}_positive_reference.npz",
            {"positive_reference_embeddings", "similarity_threshold_positive_p10", "top_k"},
        )
        for name in ("acne", "dark_circle")
    }

    support, dual = age["support"], age["dual"]
    if support.ndim != 2 or support.shape[0] < 50 or support.shape[1] != 2048:
        raise ValueError("Unexpected age support dimensions")
    if dual.shape != (support.shape[0],):
        raise ValueError("Unexpected age regression dimensions")
    if float(age["alpha"]) <= 0 or float(age["age_label_min"]) > float(age["age_label_max"]):
        raise ValueError("Invalid age regression metadata")
    for name, arrays in references.items():
        embeddings = arrays["positive_reference_embeddings"]
        top_k = int(arrays["top_k"])
        threshold = float(arrays["similarity_threshold_positive_p10"])
        if embeddings.ndim != 2 or embeddings.shape[1] != 2048 or embeddings.shape[0] < 50:
            raise ValueError(f"Unexpected {name} reference dimensions")
        if not 1 <= top_k <= embeddings.shape[0] or not -1.0 <= threshold <= 1.0:
            raise ValueError(f"Invalid {name} reference metadata")
    if not 0 <= float(skin_metrics.get("development_accuracy", -1)) <= 1:
        raise ValueError("Invalid exploratory skin-type metric")

    return ArtifactBundle(model, skin_metrics, component_metrics, age, references)
