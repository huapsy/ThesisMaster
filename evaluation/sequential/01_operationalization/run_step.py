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


def parse_args(argv: Optional[Sequence[str]] = None) -> tuple[argparse.Namespace, list[str]]:
    root = sequential_root()
    parser = argparse.ArgumentParser(description="Step 01: operationalize free-text complaints.")
    parser.add_argument("--python-exe", type=str, default=default_python_executable())
    parser.add_argument(
        "--input-txt",
        type=str,
        default=str(root / "utils/free_text/free_text_complaints.txt"),
    )
    parser.add_argument(
        "--output-csv",
        type=str,
        default=str(root / "01_operationalization/outputs/mapped_criterions.csv"),
    )
    parser.add_argument("--max-workers", type=int, default=12)
    parser.add_argument("--limit", type=int, default=0)
    parser.add_argument("--disable-llm-rerank", action=argparse.BooleanOptionalAction, default=False)
    parser.add_argument("--dry-run", action="store_true")
    return parser.parse_known_args(argv)


def main(argv: Optional[Sequence[str]] = None) -> int:
    args, passthrough = parse_args(argv)
    target = (
        sequential_root().parents[1]
        / "src/backend/SystemComponents/Agentic_Framework/01_OperationalizationMentalHealthProblem/utils/02_operationalize_freetext_complaints.py"
    )

    output_csv = Path(args.output_csv).expanduser().resolve()
    output_csv.parent.mkdir(parents=True, exist_ok=True)

    script_args = [
        "--input-txt",
        str(Path(args.input_txt).expanduser().resolve()),
        "--output-csv",
        str(output_csv),
        "--max-workers",
        str(int(args.max_workers)),
    ]
    if int(args.limit) > 0:
        script_args.extend(["--limit", str(int(args.limit))])
    if bool(args.disable_llm_rerank):
        script_args.append("--no-llm-rerank")
    script_args.extend(passthrough)

    return run_python_script(
        step_label="Step 01 - Operationalization",
        script_path=target,
        script_args=script_args,
        dry_run=bool(args.dry_run),
    )


if __name__ == "__main__":
    raise SystemExit(main())
