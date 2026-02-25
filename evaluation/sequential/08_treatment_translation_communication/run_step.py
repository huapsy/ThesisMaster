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
    parser = argparse.ArgumentParser(description="Step 08: treatment translation communication.")
    parser.add_argument("--python-exe", type=str, default=default_python_executable())
    parser.add_argument(
        "--handoff-root",
        type=str,
        default=str(root / "06_target_identification_and_model_update/outputs"),
    )
    parser.add_argument(
        "--intervention-root",
        type=str,
        default=str(root / "07_hapa_digital_intervention/outputs"),
    )
    parser.add_argument(
        "--impact-root",
        type=str,
        default=str(root / "05_momentary_impact_quantification/outputs"),
    )
    parser.add_argument(
        "--output-root",
        type=str,
        default=str(root / "08_treatment_translation_communication/outputs"),
    )
    parser.add_argument("--pattern", type=str, default="pseudoprofile_FTC_")
    parser.add_argument("--max-profiles", type=int, default=0)
    parser.add_argument("--max-workers", type=int, default=4)
    parser.add_argument("--llm-model", type=str, default="gpt-5-nano")
    parser.add_argument("--disable-llm", action=argparse.BooleanOptionalAction, default=False)
    parser.add_argument("--dry-run", action="store_true")
    return parser.parse_known_args(argv)


def main(argv: Optional[Sequence[str]] = None) -> int:
    args, passthrough = parse_args(argv)
    target = sequential_root().parents[1] / "evaluation/integrated_pipeline/stages/07_generate_treatment_translation_summary.py"

    output_root = Path(args.output_root).expanduser().resolve()
    output_root.mkdir(parents=True, exist_ok=True)

    script_args = [
        "--handoff-root",
        str(Path(args.handoff_root).expanduser().resolve()),
        "--intervention-root",
        str(Path(args.intervention_root).expanduser().resolve()),
        "--impact-root",
        str(Path(args.impact_root).expanduser().resolve()),
        "--output-root",
        str(output_root),
        "--pattern",
        str(args.pattern),
        "--max-profiles",
        str(int(args.max_profiles)),
        "--max-workers",
        str(int(args.max_workers)),
        "--llm-model",
        str(args.llm_model),
    ]
    if bool(args.disable_llm):
        script_args.append("--disable-llm")
    script_args.extend(passthrough)

    return run_python_script(
        step_label="Step 08 - Treatment Translation Communication",
        script_path=target,
        script_args=script_args,
        dry_run=bool(args.dry_run),
    )


if __name__ == "__main__":
    raise SystemExit(main())
