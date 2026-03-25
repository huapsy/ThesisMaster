from __future__ import annotations

from pathlib import Path


SURVEY_ROOT = Path(__file__).resolve().parents[2]
DATA_DIR = SURVEY_ROOT / "data"
RESULTS_DIR = SURVEY_ROOT / "results"


def ensure_study_dirs(study_slug: str) -> dict[str, Path]:
    study_root = RESULTS_DIR / study_slug
    report_dir = study_root / "report"
    visuals_dir = study_root / "visuals"
    report_dir.mkdir(parents=True, exist_ok=True)
    visuals_dir.mkdir(parents=True, exist_ok=True)
    return {
        "study_root": study_root,
        "report_dir": report_dir,
        "visuals_dir": visuals_dir,
    }


def data_file(filename: str) -> Path:
    return DATA_DIR / filename
