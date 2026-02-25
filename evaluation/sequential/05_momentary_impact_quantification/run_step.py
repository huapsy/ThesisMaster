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
    parser = argparse.ArgumentParser(description="Step 05: momentary impact quantification.")
    parser.add_argument("--python-exe", type=str, default=default_python_executable())
    parser.add_argument(
        "--input-root",
        type=str,
        default=str(root / "04_network_time_series_analysis/outputs"),
    )
    parser.add_argument(
        "--output-root",
        type=str,
        default=str(root / "05_momentary_impact_quantification/outputs"),
    )
    parser.add_argument("--pattern", type=str, default="")
    parser.add_argument("--half-life", type=float, default=0.20)
    parser.add_argument("--max-profiles", type=int, default=0)
    parser.add_argument("--top-k-edges", type=int, default=200)
    parser.add_argument("--dry-run", action="store_true")
    return parser.parse_known_args(argv)


def main(argv: Optional[Sequence[str]] = None) -> int:
    args, passthrough = parse_args(argv)
    target = (
        sequential_root().parents[1]
        / "src/SystemComponents/Hierarchical_Updating_Algorithm/02_hierarchical_update_ranking/01_momentary_impact_quantification/01_compute_momentary_impact_coefficients.py"
    )

    output_root = Path(args.output_root).expanduser().resolve()
    output_root.mkdir(parents=True, exist_ok=True)

    script_args = [
        "--input-root",
        str(Path(args.input_root).expanduser().resolve()),
        "--output-root",
        str(output_root),
        "--pattern",
        str(args.pattern),
        "--half-life",
        str(float(args.half_life)),
        "--max-profiles",
        str(int(args.max_profiles)),
        "--top-k-edges",
        str(int(args.top_k_edges)),
    ]
    script_args.extend(passthrough)

    return run_python_script(
        step_label="Step 05 - Momentary Impact Quantification",
        script_path=target,
        script_args=script_args,
        dry_run=bool(args.dry_run),
    )


if __name__ == "__main__":
    raise SystemExit(main())
