#!/usr/bin/env python3
"""
run_pipeline.py

Future-ready PHOENIX pipeline entrypoint.

Current mode:
- synthetic_v1: delegates to run_engine_pipeline.py

Planned future modes:
- full_engine: end-to-end integration with Agentic steps 03-05 and UI orchestration
"""

from __future__ import annotations

import argparse
import os
import subprocess
import sys
from datetime import datetime
from pathlib import Path
from typing import Optional, Sequence

try:
    from dotenv import load_dotenv  # type: ignore
except Exception:  # pragma: no cover - optional dependency
    load_dotenv = None  # type: ignore[assignment]


def _evaluation_root(repo_root: Path) -> Path:
    low = repo_root / "evaluation"
    if low.exists():
        return low
    up = repo_root / "Evaluation"
    if up.exists():
        return up
    return low


def _default_python_exe(repo_root: Path) -> str:
    for candidate in (
        repo_root / ".venv/bin/python",
        repo_root / ".venv/bin/python3",
    ):
        if candidate.exists():
            return str(candidate)
    return sys.executable


def _bootstrap_env(repo_root: Path) -> None:
    dotenv_path = repo_root / ".env"
    if load_dotenv is not None and dotenv_path.exists():
        load_dotenv(dotenv_path=str(dotenv_path), override=False)

    openrouter_api_key = str(os.environ.get("OPENROUTER_API_KEY") or "").strip()
    if openrouter_api_key:
        os.environ["OPENAI_API_KEY"] = openrouter_api_key
        if not str(os.environ.get("OPENAI_BASE_URL") or "").strip():
            os.environ["OPENAI_BASE_URL"] = "https://openrouter.ai/api/v1"


def _extract_passthrough_option(args: Sequence[str], option_name: str) -> tuple[list[str], str]:
    """Extract one option from passthrough args and return (remaining_args, last_value)."""
    remaining: list[str] = []
    found_value = ""
    i = 0
    while i < len(args):
        token = str(args[i])
        if token == option_name:
            if i + 1 < len(args):
                found_value = str(args[i + 1])
                i += 2
                continue
            i += 1
            continue
        if token.startswith(f"{option_name}="):
            found_value = token.split("=", 1)[1].strip()
            i += 1
            continue
        remaining.append(token)
        i += 1
    return remaining, found_value


def parse_args(argv: Optional[Sequence[str]] = None) -> tuple[argparse.Namespace, list[str]]:
    repo_root = Path(__file__).resolve().parents[2]
    parser = argparse.ArgumentParser(
        description="PHOENIX Engine pipeline launcher with mode-based routing."
    )
    parser.add_argument(
        "--mode",
        type=str,
        default="synthetic_v1",
        choices=["synthetic_v1", "full_engine"],
        help="Pipeline mode. Use synthetic_v1 for current thesis evaluation flow.",
    )
    parser.add_argument(
        "--ui",
        action=argparse.BooleanOptionalAction,
        default=False,
        help="Launch the PHOENIX Flask frontend dashboard instead of CLI cycle execution.",
    )
    parser.add_argument("--ui-host", type=str, default="127.0.0.1")
    parser.add_argument("--ui-port", type=int, default=5050)
    parser.add_argument("--ui-debug", action=argparse.BooleanOptionalAction, default=True)
    parser.add_argument("--python-exe", type=str, default=_default_python_exe(repo_root))
    parser.add_argument(
        "--run-id",
        type=str,
        default="",
        help="Explicit run id. If omitted, a timestamped run id is generated.",
    )
    parser.add_argument(
        "--dry-run",
        action=argparse.BooleanOptionalAction,
        default=False,
        help="Print resolved commands/configuration and exit without executing engine runs.",
    )
    parser.add_argument(
        "--print-effective-config",
        action=argparse.BooleanOptionalAction,
        default=True,
        help="Print resolved runtime configuration before launch.",
    )
    parser.add_argument(
        "--disable-llm",
        "--disable_LLM",
        dest="disable_llm",
        action=argparse.BooleanOptionalAction,
        default=False,
        help="Global switch to disable all LLM-dependent stages where fallbacks exist.",
    )
    parser.add_argument("--cycles", type=int, default=1, help="Number of iterative pipeline cycles to execute.")
    parser.add_argument(
        "--resume-from-run",
        type=str,
        default="",
        help="Optional prior run_id to use as memory seed when iterative memory is enabled.",
    )
    parser.add_argument(
        "--history-root",
        type=str,
        default="",
        help="Optional persistent history root. Defaults to evaluation/integrated_pipeline/runs/_history.",
    )
    parser.add_argument(
        "--profile-memory-window",
        type=int,
        default=3,
        help="How many prior cycles to include when assembling profile memory.",
    )
    return parser.parse_known_args(argv)


def main(argv: Optional[Sequence[str]] = None) -> int:
    args, passthrough = parse_args(argv)
    repo_root = Path(__file__).resolve().parents[2]
    _bootstrap_env(repo_root)
    evaluation_root = _evaluation_root(repo_root)

    if args.mode == "full_engine":
        print(
            "[PHOENIX] mode=full_engine is reserved for future integration (Agentic steps 03-05 + UI).",
            flush=True,
        )
        print(
            "[PHOENIX] Use --mode synthetic_v1 for the current research pipeline.",
            flush=True,
        )
        return 2

    if bool(args.ui):
        frontend_entry = repo_root / "src/frontend/app.py"
        env = os.environ.copy()
        env["PHOENIX_REPO_ROOT"] = str(repo_root)
        env["PHOENIX_UI_HOST"] = str(args.ui_host)
        env["PHOENIX_UI_PORT"] = str(int(args.ui_port))
        env["PHOENIX_UI_DEBUG"] = "true" if bool(args.ui_debug) else "false"
        env["PHOENIX_DISABLE_LLM"] = "true" if bool(args.disable_llm) else "false"
        print(f"[PHOENIX] Launching frontend at http://{args.ui_host}:{int(args.ui_port)}", flush=True)
        proc = subprocess.run([args.python_exe, str(frontend_entry)], check=False, env=env)
        return int(proc.returncode)

    target_script = evaluation_root / "integrated_pipeline/run_engine_pipeline.py"
    cycles = max(1, int(args.cycles))
    passthrough, passthrough_run_id = _extract_passthrough_option(passthrough, "--run-id")
    base_run_id = (
        str(args.run_id).strip()
        or str(passthrough_run_id).strip()
        or datetime.now().strftime("run_%Y%m%d_%H%M%S")
    )
    history_root = (
        Path(args.history_root).expanduser().resolve()
        if str(args.history_root).strip()
        else (evaluation_root / "integrated_pipeline/runs/_history").resolve()
    )
    if bool(args.print_effective_config):
        print(
            "[PHOENIX] Effective config: "
            f"mode={args.mode} cycles={cycles} run_id={base_run_id} "
            f"python={args.python_exe} disable_llm={bool(args.disable_llm)} "
            f"history_root={history_root}",
            flush=True,
        )
        if passthrough:
            print(f"[PHOENIX] Passthrough args: {' '.join(passthrough)}", flush=True)

    for cycle_index in range(1, cycles + 1):
        cmd = [
            args.python_exe,
            str(target_script),
            "--run-id",
            base_run_id,
            "--enable-iterative-memory",
            "--cycle-index",
            str(cycle_index),
            "--cycles",
            str(cycles),
            "--memory-policy",
            "v1_weighted_fusion",
            "--history-root",
            str(history_root),
            "--profile-memory-window",
            str(max(1, int(args.profile_memory_window))),
        ]
        if cycle_index > 1:
            cmd.append("--start-from-pseudodata")
        if bool(args.disable_llm):
            cmd.append("--disable-llm")
        if str(args.resume_from_run).strip():
            cmd.extend(["--resume-from-run", str(args.resume_from_run).strip()])
        cmd.extend(passthrough)
        print(f"[PHOENIX] Running cycle {cycle_index}/{cycles}", flush=True)
        print(f"[PHOENIX] Command: {' '.join(cmd)}", flush=True)
        if bool(args.dry_run):
            continue
        proc = subprocess.run(cmd, check=False)
        if proc.returncode != 0:
            return int(proc.returncode)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
