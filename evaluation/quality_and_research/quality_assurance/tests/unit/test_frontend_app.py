from __future__ import annotations

import sys


def test_frontend_app_boots(repo_root):
    if str(repo_root) not in sys.path:
        sys.path.insert(0, str(repo_root))
    from frontend.phoenix_frontend import create_app

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
    assert b"topbar-pipeline-nodes" in detail.data
    assert b"Workspace Control" in detail.data
    assert b"Runtime Components" in detail.data
    assert b"run-next-phase-btn" in detail.data
    assert b"Expand all sections" in detail.data
    assert b"Logs" in detail.data
    assert b"Realtime Process Logs" in detail.data
    assert b"cycle-request-refinement" in detail.data
    assert b"logs-drawer-open" in detail.data
    assert b"run-cohort-btn" in detail.data
    assert b"Advanced configuration" in detail.data
    assert b"runtime-events-list" in detail.data


def test_frontend_global_disable_llm_env(repo_root, monkeypatch):
    monkeypatch.setenv("PHOENIX_DISABLE_LLM", "true")
    if str(repo_root) not in sys.path:
        sys.path.insert(0, str(repo_root))
    from frontend.phoenix_frontend import create_app

    app = create_app()
    assert app.config.get("PHOENIX_DISABLE_LLM") is True


def test_job_stream_supports_cursor_resume(repo_root):
    if str(repo_root) not in sys.path:
        sys.path.insert(0, str(repo_root))
    from frontend.phoenix_frontend import create_app

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
