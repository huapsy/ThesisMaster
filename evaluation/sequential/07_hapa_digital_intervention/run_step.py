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
    repo = root.parents[1]
    parser = argparse.ArgumentParser(description="Step 07: generate HAPA-based digital intervention.")
    parser.add_argument("--python-exe", type=str, default=default_python_executable())
    parser.add_argument(
        "--handoff-root",
        type=str,
        default=str(root / "06_target_identification_and_model_update/outputs"),
    )
    parser.add_argument(
        "--output-root",
        type=str,
        default=str(root / "07_hapa_digital_intervention/outputs"),
    )
    parser.add_argument(
        "--readiness-root",
        type=str,
        default=str(root / "03_readiness_check/outputs"),
    )
    parser.add_argument(
        "--network-root",
        type=str,
        default=str(root / "04_network_time_series_analysis/outputs"),
    )
    parser.add_argument(
        "--impact-root",
        type=str,
        default=str(root / "05_momentary_impact_quantification/outputs"),
    )
    parser.add_argument("--free-text-root", type=str, default=str(root / "utils/free_text"))
    parser.add_argument(
        "--predictor-to-barrier-csv",
        type=str,
        default=str(
            repo
            / "src/backend/utils/official/ontology_mappings/PREDICTOR/barrier_to_predictor/results/gpt-5-nano/predictor_to_barrier_edges_long.csv"
        ),
    )
    parser.add_argument(
        "--profile-to-barrier-csv",
        type=str,
        default=str(
            repo
            / "src/backend/utils/official/ontology_mappings/HAPA/profile_to_barrier/results/gpt-5-nano/profile_to_barrier_edges_long.csv"
        ),
    )
    parser.add_argument(
        "--context-to-barrier-csv",
        type=str,
        default=str(
            repo
            / "src/backend/utils/official/ontology_mappings/HAPA/context_to_barrier/results/gpt-5-nano/context_to_barrier_edges_long.csv"
        ),
    )
    parser.add_argument(
        "--coping-to-barrier-csv",
        type=str,
        default=str(
            repo
            / "src/backend/utils/official/ontology_mappings/HAPA/coping_to_barrier/results/gpt-5-nano/coping_to_barrier_edges_long.csv"
        ),
    )
    parser.add_argument(
        "--predictor-feasibility-csv",
        type=str,
        default=str(repo / "src/backend/utils/official/multi_dimensional_feasibility_evaluation/PREDICTORS/results/summary/predictor_rankings.csv"),
    )
    parser.add_argument("--pattern", type=str, default="pseudoprofile_FTC_")
    parser.add_argument("--max-profiles", type=int, default=0)
    parser.add_argument("--top-barriers-per-predictor", type=int, default=30)
    parser.add_argument("--select-top-barriers", type=int, default=10)
    parser.add_argument("--llm-model", type=str, default="gpt-5-nano")
    parser.add_argument("--disable-llm", action=argparse.BooleanOptionalAction, default=False)
    parser.add_argument("--prompt-budget-tokens", type=int, default=400000)
    parser.add_argument("--critic-max-iterations", type=int, default=2)
    parser.add_argument("--critic-pass-threshold", type=float, default=0.74)
    parser.add_argument("--hard-ontology-constraint", action=argparse.BooleanOptionalAction, default=False)
    parser.add_argument("--parent-feasibility-top-k", type=int, default=30)
    parser.add_argument(
        "--trace-output",
        type=str,
        default=str(root / "07_hapa_digital_intervention/outputs/stage_trace_component.json"),
    )
    parser.add_argument("--dry-run", action="store_true")
    return parser.parse_known_args(argv)


def main(argv: Optional[Sequence[str]] = None) -> int:
    args, passthrough = parse_args(argv)
    target = (
        sequential_root().parents[1]
        / "src/backend/SystemComponents/Agentic_Framework/05_TranslationDigitalIntervention/01_generate_hapa_digital_intervention.py"
    )

    output_root = Path(args.output_root).expanduser().resolve()
    output_root.mkdir(parents=True, exist_ok=True)

    script_args = [
        "--handoff-root",
        str(Path(args.handoff_root).expanduser().resolve()),
        "--output-root",
        str(output_root),
        "--readiness-root",
        str(Path(args.readiness_root).expanduser().resolve()),
        "--network-root",
        str(Path(args.network_root).expanduser().resolve()),
        "--impact-root",
        str(Path(args.impact_root).expanduser().resolve()),
        "--free-text-root",
        str(Path(args.free_text_root).expanduser().resolve()),
        "--predictor-to-barrier-csv",
        str(Path(args.predictor_to_barrier_csv).expanduser().resolve()),
        "--profile-to-barrier-csv",
        str(Path(args.profile_to_barrier_csv).expanduser().resolve()),
        "--context-to-barrier-csv",
        str(Path(args.context_to_barrier_csv).expanduser().resolve()),
        "--coping-to-barrier-csv",
        str(Path(args.coping_to_barrier_csv).expanduser().resolve()),
        "--predictor-feasibility-csv",
        str(Path(args.predictor_feasibility_csv).expanduser().resolve()),
        "--pattern",
        str(args.pattern),
        "--max-profiles",
        str(int(args.max_profiles)),
        "--top-barriers-per-predictor",
        str(int(args.top_barriers_per_predictor)),
        "--select-top-barriers",
        str(int(args.select_top_barriers)),
        "--llm-model",
        str(args.llm_model),
        "--prompt-budget-tokens",
        str(int(args.prompt_budget_tokens)),
        "--critic-max-iterations",
        str(int(args.critic_max_iterations)),
        "--critic-pass-threshold",
        str(float(args.critic_pass_threshold)),
        "--parent-feasibility-top-k",
        str(int(args.parent_feasibility_top_k)),
        "--trace-output",
        str(Path(args.trace_output).expanduser().resolve()),
    ]
    if bool(args.disable_llm):
        script_args.append("--disable-llm")
    if bool(args.hard_ontology_constraint):
        script_args.append("--hard-ontology-constraint")
    script_args.extend(passthrough)

    return run_python_script(
        step_label="Step 07 - HAPA Digital Intervention",
        script_path=target,
        script_args=script_args,
        dry_run=bool(args.dry_run),
    )


if __name__ == "__main__":
    raise SystemExit(main())
