from __future__ import annotations

import sys


def test_frontend_app_boots(repo_root):
    if str(repo_root) not in sys.path:
        sys.path.insert(0, str(repo_root))
    from src.frontend.phoenix_frontend import create_app

    app = create_app()
    client = app.test_client()
    resp = client.get("/")
    assert resp.status_code == 200
    assert b"PHOENIX" in resp.data

    created = client.post(
        "/sessions/new",
        data={"complaint_text": "I feel persistently down and unmotivated."},
        follow_redirects=False,
    )
    assert created.status_code in {302, 303}
    location = created.headers.get("Location", "")
    assert "/sessions/" in location

    detail = client.get(location)
    assert detail.status_code == 200
    assert b"id=\"topbar-pipeline-nodes\"" in detail.data
    assert b"Full Pipeline Run" in detail.data
    assert b"Cohort Sandbox" in detail.data
    assert b"Runtime Components" in detail.data
    assert b"id=\"run-next-phase-btn\"" in detail.data
    assert b"Step 01 final leaf adjudication (LLM)" in detail.data
    assert b"local LLM critic refinement" in detail.data
    assert b"Logs" in detail.data
    assert b"Process Logs" in detail.data
    assert b"cycle-request-refinement" in detail.data
    assert b"runtime-events-list" in detail.data
    assert b"run-cohort-btn" in detail.data


def test_frontend_global_disable_llm_env(repo_root, monkeypatch):
    monkeypatch.setenv("PHOENIX_DISABLE_LLM", "true")
    if str(repo_root) not in sys.path:
        sys.path.insert(0, str(repo_root))
    from src.frontend.phoenix_frontend import create_app

    app = create_app()
    assert app.config.get("PHOENIX_DISABLE_LLM") is True


def test_job_stream_supports_cursor_resume(repo_root):
    if str(repo_root) not in sys.path:
        sys.path.insert(0, str(repo_root))
    from src.frontend.phoenix_frontend import create_app

    app = create_app()
    manager = app.extensions["phoenix.job_manager"]

    def _target(log):
        log("alpha", "INFO")
        log("beta", "INFO")
        return {"ok": True}

    job_id = manager.start_job(session_id="s_stream_test", kind="initial_model", target=_target)
    manager.wait_until_complete(job_id, timeout_seconds=5.0)

    client = app.test_client()
    response_all = client.get(f"/api/jobs/{job_id}/stream?after=0")
    text_all = response_all.data.decode("utf-8")
    assert response_all.status_code == 200
    assert '"type": "log"' in text_all
    assert '"line": "alpha"' in text_all
    assert '"line": "beta"' in text_all
    assert '"type": "status"' in text_all

    response_after_one = client.get(f"/api/jobs/{job_id}/stream?after=1")
    text_after_one = response_after_one.data.decode("utf-8")
    assert response_after_one.status_code == 200
    assert '"line": "alpha"' not in text_after_one
    assert '"line": "beta"' in text_after_one
    assert '"type": "status"' in text_after_one


def test_full_session_pipeline_job_endpoint(repo_root, monkeypatch):
    if str(repo_root) not in sys.path:
        sys.path.insert(0, str(repo_root))
    from src.frontend.phoenix_frontend import create_app

    app = create_app()
    store = app.extensions["phoenix.session_store"]
    service = app.extensions["phoenix.service"]
    session = store.create_session(complaint_text="Low mood with unstable energy and concentration.")

    def _fake_run_full_session_pipeline(**kwargs):
        log = kwargs["log"]
        log("[component:full_session_pipeline] status=running", "INFO")
        log("[component:full_session_pipeline] status=succeeded", "INFO")
        return {"cycles_requested": 1, "cycles_completed": 1}

    monkeypatch.setattr(service, "run_full_session_pipeline", _fake_run_full_session_pipeline)

    client = app.test_client()
    resp = client.post(f"/api/sessions/{session.session_id}/jobs/run-full", json={"cycles": 1})
    assert resp.status_code == 200
    payload = resp.get_json() or {}
    assert payload.get("status") == "ok"
    job_id = str(payload.get("job_id") or "")
    assert job_id.startswith("job_")

    terminal_status = ""
    for _ in range(40):
        poll = client.get(f"/api/jobs/{job_id}")
        assert poll.status_code == 200
        row = poll.get_json() or {}
        terminal_status = str(((row.get("job") or {}).get("status") or "")).lower()
        if terminal_status in {"succeeded", "failed"}:
            break
    assert terminal_status == "succeeded"


def test_update_session_intake_endpoint(repo_root):
    if str(repo_root) not in sys.path:
        sys.path.insert(0, str(repo_root))
    from src.frontend.phoenix_frontend import create_app

    app = create_app()
    store = app.extensions["phoenix.session_store"]
    session = store.create_session(
        complaint_text="Old complaint text.",
        person_text="Old person context.",
        context_text="Old environment context.",
    )

    client = app.test_client()
    resp = client.patch(
        f"/api/sessions/{session.session_id}/intake",
        json={
            "complaint_text": "Updated complaint text for testing.",
            "person_text": "Updated person context.",
            "context_text": "Updated environment context.",
            "reset_outputs": True,
        },
    )
    assert resp.status_code == 200
    payload = resp.get_json() or {}
    assert payload.get("status") == "ok"
    assert (payload.get("session") or {}).get("complaint_text") == "Updated complaint text for testing."
    intake_sync = payload.get("intake_sync") or {}
    assert intake_sync.get("matches") is True
