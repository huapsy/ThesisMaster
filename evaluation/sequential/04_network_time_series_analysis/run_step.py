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

from common import default_python_executable, run_python_script, sequential_root


def parse_args(argv: Optional[Sequence[str]] = None) -> tuple[argparse.Namespace, list[str]]:
    root = sequential_root()
    parser = argparse.ArgumentParser(description="Step 04: network time-series analysis.")
    parser.add_argument("--python-exe", type=str, default=default_python_executable())
    parser.add_argument(
        "--input-root",
        type=str,
        default=str(root / "00_pseudoprofile_generation/outputs/pseudodata"),
    )
    parser.add_argument(
        "--readiness-root",
        type=str,
        default=str(root / "03_readiness_check/outputs"),
    )
    parser.add_argument(
        "--output-root",
        type=str,
        default=str(root / "04_network_time_series_analysis/outputs"),
    )
    parser.add_argument("--data-filename", type=str, default="pseudodata_wide.csv")
    parser.add_argument("--metadata-filename", type=str, default="variables_metadata.csv")
    parser.add_argument("--readiness-filename", type=str, default="readiness_report.json")
    parser.add_argument("--pattern", type=str, default="")
    parser.add_argument("--max-profiles", type=int, default=0)
    parser.add_argument(
        "--prefer-tier",
        type=str,
        default="overall_ready",
        choices=["tier1", "overall_ready", "all_non_hard"],
    )
    parser.add_argument(
        "--execution-policy",
        type=str,
        default="readiness_aligned",
        choices=["readiness_aligned", "all_methods"],
    )
    parser.add_argument("--boot", type=int, default=80)
    parser.add_argument("--block-len", type=int, default=20)
    parser.add_argument("--jobs", type=int, default=1)
    parser.add_argument("--verbose", action=argparse.BooleanOptionalAction, default=True)
    parser.add_argument("--dry-run", action="store_true")
    return parser.parse_known_args(argv)


def main(argv: Optional[Sequence[str]] = None) -> int:
    args, passthrough = parse_args(argv)
    target = (
        sequential_root().parents[1]
        / "src/SystemComponents/Hierarchical_Updating_Algorithm/01_time_series_analysis/02_network_time_series_analysis/01_run_network_ts_analysis.py"
    )

    output_root = Path(args.output_root).expanduser().resolve()
    output_root.mkdir(parents=True, exist_ok=True)

    script_args = [
        "--input-root",
        str(Path(args.input_root).expanduser().resolve()),
        "--readiness-root",
        str(Path(args.readiness_root).expanduser().resolve()),
        "--output-root",
        str(output_root),
        "--data-filename",
        str(args.data_filename),
        "--metadata-filename",
        str(args.metadata_filename),
        "--readiness-filename",
        str(args.readiness_filename),
        "--pattern",
        str(args.pattern),
        "--max-profiles",
        str(int(args.max_profiles)),
        "--prefer-tier",
        str(args.prefer_tier),
        "--execution-policy",
        str(args.execution_policy),
        "--boot",
        str(int(args.boot)),
        "--block-len",
        str(int(args.block_len)),
        "--jobs",
        str(int(args.jobs)),
    ]
    if bool(args.verbose):
        script_args.append("--verbose")
    else:
        script_args.append("--no-verbose")
    script_args.extend(passthrough)

    return run_python_script(
        step_label="Step 04 - Network Time-Series Analysis",
        script_path=target,
        script_args=script_args,
        dry_run=bool(args.dry_run),
    )


if __name__ == "__main__":
    raise SystemExit(main())
