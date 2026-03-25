#!/usr/bin/env python3
from __future__ import annotations

import os
import runpy
import subprocess
import sys
from pathlib import Path
from typing import Mapping, Optional, Sequence

try:
    from dotenv import load_dotenv  # type: ignore
except Exception:  # pragma: no cover - optional dependency
    load_dotenv = None  # type: ignore[assignment]


def repo_root() -> Path:
    here = Path(__file__).resolve()
    for candidate in [here, *here.parents]:
        if (candidate / "README.md").exists() and (candidate / "evaluation").exists():
            return candidate
    raise RuntimeError("Could not locate repository root from evaluation/sequential/utils/common.py")


def evaluation_root() -> Path:
    root = repo_root()
    low = root / "evaluation"
    if low.exists():
        return low
    up = root / "Evaluation"
    if up.exists():
        return up
    return low


def sequential_root() -> Path:
    return evaluation_root() / "sequential"


def default_python_executable() -> str:
    root = repo_root()
    candidates = (
        root / ".venv/bin/python",
        root / ".venv/bin/python3",
    )
    for candidate in candidates:
        if candidate.exists():
            return str(candidate)
    return sys.executable


def bool_token(value: bool) -> str:
    return "True" if bool(value) else "False"


def parse_boolish(value: object) -> bool:
    if isinstance(value, bool):
        return value
    token = str(value).strip().lower()
    return token in {"1", "true", "t", "yes", "y", "on"}


def _apply_openrouter_env_compat() -> None:
    if load_dotenv is not None:
        dotenv_path = repo_root() / ".env"
        if dotenv_path.exists():
            load_dotenv(dotenv_path=str(dotenv_path), override=False)

    openrouter_api_key = str(os.environ.get("OPENROUTER_API_KEY") or "").strip()
    if not openrouter_api_key:
        return
    os.environ["OPENAI_API_KEY"] = openrouter_api_key
    if not str(os.environ.get("OPENAI_BASE_URL") or "").strip():
        os.environ["OPENAI_BASE_URL"] = "https://openrouter.ai/api/v1"


def run_command(
    *,
    step_label: str,
    command: Sequence[str],
    dry_run: bool = False,
    env: Optional[Mapping[str, str]] = None,
) -> int:
    _apply_openrouter_env_compat()
    cmd = [str(item) for item in command]
    print(f"[PHOENIX][sequential] {step_label}", flush=True)
    print(f"[PHOENIX][sequential] command: {' '.join(cmd)}", flush=True)
    if dry_run:
        return 0
    proc = subprocess.run(cmd, check=False, env=dict(env) if env else None)
    return int(proc.returncode)


def run_python_script(
    *,
    step_label: str,
    script_path: Path,
    script_args: Sequence[str],
    dry_run: bool = False,
) -> int:
    _apply_openrouter_env_compat()
    cmd = [str(script_path), *[str(x) for x in script_args]]
    print(f"[PHOENIX][sequential] {step_label}", flush=True)
    print(f"[PHOENIX][sequential] script: {' '.join(cmd)}", flush=True)
    if dry_run:
        return 0

    old_argv = sys.argv[:]
    sys.argv = [str(script_path), *[str(x) for x in script_args]]
    try:
        runpy.run_path(str(script_path), run_name="__main__")
        return 0
    except SystemExit as exc:
        code = exc.code
        if code is None:
            return 0
        if isinstance(code, int):
            return int(code)
        return 1
    finally:
        sys.argv = old_argv
