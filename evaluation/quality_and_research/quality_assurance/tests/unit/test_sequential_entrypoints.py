from __future__ import annotations

from pathlib import Path

import pytest

pytestmark = pytest.mark.unit


def test_sequential_entrypoints_exist(repo_file_fn) -> None:
    expected = [
        "evaluation/sequential/00_pseudoprofile_generation/run_step.py",
        "evaluation/sequential/01_operationalization/run_step.py",
        "evaluation/sequential/02_initial_observation_model/run_step.py",
        "evaluation/sequential/03_readiness_check/run_step.py",
        "evaluation/sequential/04_network_time_series_analysis/run_step.py",
        "evaluation/sequential/05_momentary_impact_quantification/run_step.py",
        "evaluation/sequential/06_target_identification_and_model_update/run_step.py",
        "evaluation/sequential/07_hapa_digital_intervention/run_step.py",
        "evaluation/sequential/08_treatment_translation_communication/run_step.py",
    ]
    for rel in expected:
        path = Path(repo_file_fn(rel))
        assert path.exists(), f"missing sequential entrypoint: {rel}"
