from __future__ import annotations

import pytest

pytestmark = pytest.mark.unit


def test_flow_registry_builds_engine_and_support_statuses(module_loader, repo_file_fn):
    module = module_loader(
        str(repo_file_fn("evaluation/integrated_pipeline/stages/flow_registry.py")),
        "phoenix_flow_registry_module",
    )
    stage_results = [
        {"stage": "readiness", "return_code": 0, "duration_seconds": 1.0, "command": ["python"], "log_path": "a"},
        {"stage": "network", "return_code": 0, "duration_seconds": 2.0, "command": ["python"], "log_path": "b"},
        {"stage": "impact", "return_code": 0, "duration_seconds": 3.0, "command": ["python"], "log_path": "c"},
        {"stage": "handoff", "return_code": 0, "duration_seconds": 4.0, "command": ["python"], "log_path": "d"},
        {"stage": "intervention", "return_code": 0, "duration_seconds": 5.0, "command": ["python"], "log_path": "e"},
        {"stage": "translation_communication", "return_code": 0, "duration_seconds": 1.5, "command": ["python"], "log_path": "f"},
        {"stage": "visualization", "return_code": 0, "duration_seconds": 0.8, "command": ["python"], "log_path": "g"},
        {"stage": "reporting", "return_code": 0, "duration_seconds": 0.6, "command": ["python"], "log_path": "h"},
    ]

    payload = module.build_flow_summary(
        stage_results=stage_results,
        step03_generated=True,
        step04_generated=True,
        step05_generated=True,
        translation_generated=True,
        pseudodata_ready=True,
        iterative_update_generated=True,
    )

    engine = payload.get("engine_stage_flow") or []
    support = payload.get("quality_and_research_flow") or []
    assert engine
    assert support
    statuses = {row["stage_id"]: row["status"] for row in engine}
    assert statuses["pseudodata_generation"] == "succeeded"
    assert statuses["treatment_target_identification"] == "succeeded"
    assert statuses["updated_observation_model"] == "succeeded"
    assert statuses["digital_intervention_translation"] == "succeeded"
    assert statuses["treatment_translation_communication"] == "succeeded"
    assert statuses["iterative_model_update"] == "succeeded"
    support_statuses = {row["stage_id"]: row["status"] for row in support}
    assert support_statuses["impact_visualization_support"] == "succeeded"
    assert support_statuses["research_reporting_support"] == "succeeded"
