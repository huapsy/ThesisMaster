from __future__ import annotations

import sys
import json
from pathlib import Path

import pytest

pytestmark = pytest.mark.unit


def _load_service_module(repo_root):
    if str(repo_root) not in sys.path:
        sys.path.insert(0, str(repo_root))
    from frontend.phoenix_frontend.services import phoenix_service as module

    return module


def test_extract_step02_worker_error_prefers_profile_row(repo_root, tmp_path: Path):
    module = _load_service_module(repo_root)
    run_dir = tmp_path / "runs" / "frontend_run_x"
    run_dir.mkdir(parents=True, exist_ok=True)
    errors_csv = run_dir / "errors.csv"
    errors_csv.write_text(
        "pseudoprofile_id,error_message\n"
        "pseudoprofile_A,TypeError: mismatch\n"
        "pseudoprofile_B,RuntimeError: failed\n",
        encoding="utf-8",
    )

    service = module.PhoenixService.__new__(module.PhoenixService)
    message = module.PhoenixService._extract_step02_worker_error(
        service,
        run_dir=run_dir,
        profile_id="pseudoprofile_B",
    )
    assert "RuntimeError: failed" in message


def test_extract_step02_worker_error_empty_when_missing(repo_root, tmp_path: Path):
    module = _load_service_module(repo_root)
    run_dir = tmp_path / "runs" / "frontend_run_y"
    run_dir.mkdir(parents=True, exist_ok=True)

    service = module.PhoenixService.__new__(module.PhoenixService)
    message = module.PhoenixService._extract_step02_worker_error(
        service,
        run_dir=run_dir,
        profile_id="pseudoprofile_X",
    )
    assert message == ""


def test_load_latest_communication_prefers_cycle_stage(repo_root, tmp_path: Path):
    module = _load_service_module(repo_root)
    logs_root = tmp_path / "logs"
    logs_root.mkdir(parents=True, exist_ok=True)
    (logs_root / "communication_initial_model_1.json").write_text(
        '{"stage":"initial_model","summary":{"headline":"init"}}',
        encoding="utf-8",
    )
    (logs_root / "communication_cycle_01_2.json").write_text(
        '{"stage":"cycle_01","summary":{"headline":"cycle"}}',
        encoding="utf-8",
    )

    class _Store:
        def session_paths(self, _session_id):
            return {"frontend_logs_root": logs_root}

    service = module.PhoenixService.__new__(module.PhoenixService)
    service.session_store = _Store()
    payload = module.PhoenixService._load_latest_communication_summary(service, session_id="s_test")
    assert payload
    assert payload["payload"]["stage"] == "cycle_01"


def test_run_pipeline_cycle_adds_start_from_pseudodata_after_cycle_one(repo_root, tmp_path: Path):
    module = _load_service_module(repo_root)
    from frontend.phoenix_frontend.services.session_store import SessionStore

    store = SessionStore(tmp_path / "sessions")
    session = store.create_session(
        complaint_text="test complaint",
        person_text="",
        context_text="",
        profile_id="pseudoprofile_FTC_ID001",
    )
    paths = store.session_paths(session.session_id)
    (paths["pseudodata_profile_root"] / "pseudodata_wide.csv").write_text(
        "t_index,date,P01\n0,2025-01-01,0.3\n",
        encoding="utf-8",
    )
    model_path = paths["outputs_root"] / "model.json"
    model_path.write_text(json.dumps({"model_summary": "ok"}), encoding="utf-8")
    store.update_session(
        session.session_id,
        latest_model_json=str(model_path),
        pipeline_run_id="unit_run",
        current_cycle=1,
    )

    expected_cycle_root = paths["pipeline_root"] / "unit_run" / "cycles" / "cycle_02"
    expected_cycle_root.mkdir(parents=True, exist_ok=True)
    (expected_cycle_root / "pipeline_summary.json").write_text(
        json.dumps(
            {
                "status": "ok",
                "run_id": "unit_run",
                "cycle_index": 2,
                "engine_stage_flow": [],
                "quality_and_research_flow": [],
                "stage_results": [],
            }
        ),
        encoding="utf-8",
    )

    service = module.PhoenixService(
        repo_root=repo_root,
        python_exe=sys.executable,
        session_store=store,
    )
    captured = {"cmd": []}

    def _fake_run_command(*, cmd, log, env=None, component="", mark_success=True):  # noqa: ANN001
        captured["cmd"] = list(cmd)

    service._run_command = _fake_run_command  # type: ignore[method-assign]
    service._write_communication_summary = lambda **_: {"path": "", "payload": {}}  # type: ignore[assignment]

    result = service.run_pipeline_cycle(
        session_id=session.session_id,
        hard_ontology_constraint=False,
        llm_model="gpt-5-nano",
        disable_llm=True,
        include_intervention=True,
        request_model_refinement=False,
        profile_memory_window=3,
        handoff_critic_max_iterations=2,
        handoff_critic_pass_threshold=0.74,
        intervention_critic_max_iterations=2,
        intervention_critic_pass_threshold=0.74,
        network_boot=40,
        network_block_len=14,
        network_jobs=1,
        run_impact_visualizations=False,
        run_treatment_communication=False,
        parallel_branches=True,
        log=lambda *_: None,
    )

    assert "--start-from-pseudodata" in captured["cmd"]
    assert result["cycle_index"] == 2
