from __future__ import annotations

import sys


def test_frontend_config_defaults_resolve_repo_and_workspace(repo_root, monkeypatch):
    monkeypatch.delenv("PHOENIX_REPO_ROOT", raising=False)
    monkeypatch.delenv("PHOENIX_FRONTEND_WORKSPACE", raising=False)
    monkeypatch.delenv("PHOENIX_PYTHON_EXE", raising=False)

    if str(repo_root) not in sys.path:
        sys.path.insert(0, str(repo_root))

    from src.frontend.phoenix_frontend.config import load_paths

    paths = load_paths()
    assert paths.repo_root == repo_root.resolve()
    assert paths.workspace_root == (repo_root / "src/frontend/workspace").resolve()
    assert paths.sessions_root == (repo_root / "src/frontend/workspace/sessions").resolve()
