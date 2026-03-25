from __future__ import annotations

import os
import sys
from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class FrontendPaths:
    repo_root: Path
    workspace_root: Path
    sessions_root: Path
    python_exe: str


def _discover_repo_root() -> Path:
    here = Path(__file__).resolve()
    for candidate in [here, *here.parents]:
        has_eval = (candidate / "evaluation").exists() or (candidate / "Evaluation").exists()
        if has_eval and (candidate / "README.md").exists():
            return candidate
    raise RuntimeError("Could not locate repository root from frontend config.")


def load_paths() -> FrontendPaths:
    default_repo_root = _discover_repo_root()
    repo_root = Path(os.environ.get("PHOENIX_REPO_ROOT", str(default_repo_root))).expanduser().resolve()
    default_workspace = repo_root / "src" / "frontend" / "workspace"
    workspace_root = Path(
        os.environ.get("PHOENIX_FRONTEND_WORKSPACE", str(default_workspace))
    ).expanduser().resolve()
    sessions_root = workspace_root / "sessions"
    python_exe = os.environ.get("PHOENIX_PYTHON_EXE", sys.executable)
    return FrontendPaths(
        repo_root=repo_root,
        workspace_root=workspace_root,
        sessions_root=sessions_root,
        python_exe=python_exe,
    )
