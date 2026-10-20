"""Application configuration with repository-relative defaults."""
from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parent.parent


@dataclass(frozen=True)
class AppConfig:
    project_root: Path = PROJECT_ROOT
    host: str = "127.0.0.1"
    port: int = 0
    max_image_bytes: int = 10 * 1024 * 1024
    max_pixels: int = 20_000_000
    min_image_side: int = 512
    max_preview_side: int = 960
    skin_run: str = "skin_type_phase6k_finetune_83076473ef76"
    components_run: str = "phase6l_other_components_1e261ce2d702"

    @property
    def model_version(self) -> str:
        return "phase6k-83076473ef76+phase6l-1e261ce2d702"
