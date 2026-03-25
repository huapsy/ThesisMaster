#!/usr/bin/env python3
from __future__ import annotations

import argparse
import sys
from pathlib import Path
from typing import Optional, Sequence

THIS_DIR = Path(__file__).resolve().parent
SEQUENTIAL_ROOT = THIS_DIR.parent
if str(SEQUENTIAL_ROOT) not in sys.path:
    sys.path.insert(0, str(SEQUENTIAL_ROOT))

from utils.common import default_python_executable, run_python_script, sequential_root


def parse_args(argv: Optional[Sequence[str]] = None) -> argparse.Namespace:
    root = sequential_root()
    parser = argparse.ArgumentParser(
        description="Step 00: pseudoprofile pseudodata generation and optional visualization."
    )
    parser.add_argument("--python-exe", type=str, default=default_python_executable())
    parser.add_argument(
        "--runs-root",
        type=str,
        default=str(root / "02_initial_observation_model/outputs/runs"),
        help="Root with Step-02 model runs.",
    )
    parser.add_argument("--run-id", type=str, default="", help="Optional specific Step-02 run id.")
    parser.add_argument("--mapped-pattern", type=str, default="llm_observation_model_mapped*.txt")
    parser.add_argument(
        "--out-root",
        type=str,
        default=str(root / "00_pseudoprofile_generation/outputs/pseudodata"),
    )
    parser.add_argument("--n", type=int, default=None)
    parser.add_argument("--freq", type=str, default="D")
    parser.add_argument("--start-date", type=str, default="2025-01-01")
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument("--overwrite", action=argparse.BooleanOptionalAction, default=False)
    parser.add_argument("--visualize", action=argparse.BooleanOptionalAction, default=False)
    parser.add_argument("--visualize-overwrite", action=argparse.BooleanOptionalAction, default=False)
    parser.add_argument("--dry-run", action="store_true")
    return parser.parse_args(argv)


def main(argv: Optional[Sequence[str]] = None) -> int:
    args = parse_args(argv)
    step_root = sequential_root() / "00_pseudoprofile_generation"
    utils_dir = step_root / "utils"
    create_script = utils_dir / "create_pseudodata.py"
    visualize_script = utils_dir / "visualize_time_series.py"

    out_root = Path(args.out_root).expanduser().resolve()
    out_root.mkdir(parents=True, exist_ok=True)

    create_args = [
        "--runs-root",
        str(Path(args.runs_root).expanduser().resolve()),
        "--mapped-pattern",
        str(args.mapped_pattern),
        "--out-root",
        str(out_root),
        "--freq",
        str(args.freq),
        "--start-date",
        str(args.start_date),
        "--seed",
        str(int(args.seed)),
    ]
    if args.run_id.strip():
        create_args.extend(["--run-id", args.run_id.strip()])
    if args.n is not None:
        create_args.extend(["--n", str(int(args.n))])
    if bool(args.overwrite):
        create_args.append("--overwrite")

    rc = run_python_script(
        step_label="Step 00 - Pseudoprofile Generation",
        script_path=create_script,
        script_args=create_args,
        dry_run=bool(args.dry_run),
    )
    if rc != 0:
        return rc

    if bool(args.visualize):
        viz_args = [
            "--root",
            str(out_root),
        ]
        if bool(args.visualize_overwrite):
            viz_args.append("--overwrite")
        return run_python_script(
            step_label="Step 00 - Time-Series Visualization",
            script_path=visualize_script,
            script_args=viz_args,
            dry_run=bool(args.dry_run),
        )

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
