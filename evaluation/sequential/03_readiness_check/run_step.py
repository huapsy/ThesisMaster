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

from common import bool_token, default_python_executable, parse_boolish, run_python_script, sequential_root


def parse_args(argv: Optional[Sequence[str]] = None) -> tuple[argparse.Namespace, list[str]]:
    root = sequential_root()
    parser = argparse.ArgumentParser(description="Step 03: readiness check.")
    parser.add_argument("--python-exe", type=str, default=default_python_executable())
    parser.add_argument(
        "--input-root",
        type=str,
        default=str(root / "00_pseudoprofile_generation/outputs/pseudodata"),
    )
    parser.add_argument(
        "--output-root",
        type=str,
        default=str(root / "03_readiness_check/outputs"),
    )
    parser.add_argument("--filename", type=str, default="pseudodata_wide.csv")
    parser.add_argument("--lag", type=int, default=1)
    parser.add_argument("--max-profiles", type=int, default=0)
    parser.add_argument("--llm-finalize", type=str, default="False")
    parser.add_argument("--quiet", type=str, default="False")
    parser.add_argument("--prefer-time-varying", type=str, default="True")
    parser.add_argument("--dry-run", action="store_true")
    return parser.parse_known_args(argv)


def main(argv: Optional[Sequence[str]] = None) -> int:
    args, passthrough = parse_args(argv)
    target = (
        sequential_root().parents[1]
        / "src/backend/SystemComponents/Hierarchical_Updating_Algorithm/01_time_series_analysis/01_check_readiness/apply_readiness_check.py"
    )

    output_root = Path(args.output_root).expanduser().resolve()
    output_root.mkdir(parents=True, exist_ok=True)

    script_args = [
        "--input-root",
        str(Path(args.input_root).expanduser().resolve()),
        "--output-root",
        str(output_root),
        "--filename",
        str(args.filename),
        "--lag",
        str(int(args.lag)),
        "--max-profiles",
        str(int(args.max_profiles)),
        "--llm-finalize",
        bool_token(parse_boolish(args.llm_finalize)),
        "--quiet",
        bool_token(parse_boolish(args.quiet)),
        "--prefer-time-varying",
        bool_token(parse_boolish(args.prefer_time_varying)),
    ]
    script_args.extend(passthrough)

    return run_python_script(
        step_label="Step 03 - Readiness Check",
        script_path=target,
        script_args=script_args,
        dry_run=bool(args.dry_run),
    )


if __name__ == "__main__":
    raise SystemExit(main())
