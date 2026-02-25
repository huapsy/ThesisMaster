from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

import pytest

pytestmark = pytest.mark.unit


def test_translation_communication_stage_writes_profile_outputs(tmp_path: Path, repo_file_fn) -> None:
    script = repo_file_fn("evaluation/integrated_pipeline/stages/07_generate_treatment_translation_summary.py")

    handoff_root = tmp_path / "handoff"
    intervention_root = tmp_path / "intervention"
    impact_root = tmp_path / "impact"
    output_root = tmp_path / "communication"

    profile_id = "pseudoprofile_test001"
    (handoff_root / profile_id).mkdir(parents=True)
    (intervention_root / profile_id).mkdir(parents=True)
    (impact_root / profile_id).mkdir(parents=True)

    (handoff_root / profile_id / "step03_target_selection.json").write_text(
        json.dumps({"recommended_targets": [{"predictor": "P01", "score_0_1": 0.7}]}),
        encoding="utf-8",
    )
    (handoff_root / profile_id / "step04_updated_observation_model.json").write_text(
        json.dumps({"recommended_next_observation_predictors": ["P01", "P02"]}),
        encoding="utf-8",
    )
    (intervention_root / profile_id / "step05_hapa_intervention.json").write_text(
        json.dumps(
            {
                "selected_barriers": [{"barrier_name": "Low energy", "score_0_1": 0.6}],
                "selected_coping_strategies": [{"coping_name": "Walk", "score_0_1": 0.5}],
            }
        ),
        encoding="utf-8",
    )
    (impact_root / profile_id / "predictor_composite.csv").write_text(
        "predictor,predictor_impact\nP01,0.55\nP02,0.21\n",
        encoding="utf-8",
    )

    cmd = [
        sys.executable,
        str(script),
        "--handoff-root",
        str(handoff_root),
        "--intervention-root",
        str(intervention_root),
        "--impact-root",
        str(impact_root),
        "--output-root",
        str(output_root),
        "--max-profiles",
        "1",
        "--disable-llm",
    ]
    proc = subprocess.run(cmd, check=False, capture_output=True, text=True)
    assert proc.returncode == 0, proc.stdout + "\n" + proc.stderr

    profile_json = output_root / profile_id / "treatment_translation_communication.json"
    run_summary = output_root / "translation_communication_run_summary.json"
    assert profile_json.exists()
    assert run_summary.exists()

    payload = json.loads(profile_json.read_text(encoding="utf-8"))
    assert payload["stage"] == "translation_communication"
    assert payload["profile_id"] == profile_id

    summary_payload = json.loads(run_summary.read_text(encoding="utf-8"))
    assert int(summary_payload.get("profile_count") or 0) == 1
