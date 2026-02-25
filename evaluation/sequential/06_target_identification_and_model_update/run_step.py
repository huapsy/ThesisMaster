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


def _default_hyde_dense_profiles_path() -> Path:
    runs_root = (
        sequential_root().parents[1]
        / "src/utils/agentic_core/others/initial_observation_model_assets/helpers/00_HyDe_based_predictor_ranks/runs"
    )
    candidates = sorted(runs_root.glob("*/dense_profiles.csv"))
    if candidates:
        return candidates[-1]
    return runs_root / "2026-01-15_19-51-47/dense_profiles.csv"


def parse_args(argv: Optional[Sequence[str]] = None) -> tuple[argparse.Namespace, list[str]]:
    root = sequential_root()
    repo = root.parents[1]
    parser = argparse.ArgumentParser(description="Step 06: treatment target identification and updated model.")
    parser.add_argument("--python-exe", type=str, default=default_python_executable())
    parser.add_argument(
        "--impact-root",
        type=str,
        default=str(root / "05_momentary_impact_quantification/outputs"),
    )
    parser.add_argument(
        "--output-root",
        type=str,
        default=str(root / "06_target_identification_and_model_update/outputs"),
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
        "--initial-model-runs-root",
        type=str,
        default=str(root / "02_initial_observation_model/outputs/runs"),
    )
    parser.add_argument("--free-text-root", type=str, default=str(root / "free_text"))
    parser.add_argument(
        "--mapping-ranks-csv",
        type=str,
        default=str(
            sequential_root().parents[1]
            / "src/utils/agentic_core/others/initial_observation_model_assets/helpers/00_LLM_based_mapping_based_predictor_ranks/all_pseudoprofiles__predictor_ranks_dense.csv"
        ),
    )
    parser.add_argument("--hyde-dense-profiles-csv", type=str, default=str(_default_hyde_dense_profiles_path()))
    parser.add_argument(
        "--hyde-runs-root",
        type=str,
        default=str(
            sequential_root().parents[1]
            / "src/utils/agentic_core/others/initial_observation_model_assets/helpers/00_HyDe_based_predictor_ranks/runs"
        ),
    )
    parser.add_argument(
        "--predictor-list-path",
        type=str,
        default=str(
            repo / "src/utils/official/ontology_mappings/CRITERION/predictor_to_criterion/input_lists/predictors_list.txt"
        ),
    )
    parser.add_argument(
        "--predictor-feasibility-csv",
        type=str,
        default=str(
            repo / "src/utils/official/multi_dimensional_feasibility_evaluation/PREDICTORS/results/summary/predictor_rankings.csv"
        ),
    )
    parser.add_argument("--pattern", type=str, default="pseudoprofile_FTC_")
    parser.add_argument("--max-profiles", type=int, default=0)
    parser.add_argument("--top-k", type=int, default=15)
    parser.add_argument("--min-impact", type=float, default=0.10)
    parser.add_argument("--max-candidate-predictors", type=int, default=200)
    parser.add_argument("--llm-model", type=str, default="gpt-5-nano")
    parser.add_argument("--disable-llm", action=argparse.BooleanOptionalAction, default=False)
    parser.add_argument("--prompt-budget-tokens", type=int, default=400000)
    parser.add_argument("--critic-max-iterations", type=int, default=2)
    parser.add_argument("--critic-pass-threshold", type=float, default=0.74)
    parser.add_argument("--hard-ontology-constraint", action=argparse.BooleanOptionalAction, default=False)
    parser.add_argument("--preferred-predictor-count", type=int, default=6)
    parser.add_argument("--preferred-criterion-count", type=int, default=4)
    parser.add_argument("--parent-feasibility-top-k", type=int, default=30)
    parser.add_argument(
        "--trace-output",
        type=str,
        default=str(root / "06_target_identification_and_model_update/outputs/stage_trace_component.json"),
    )
    parser.add_argument("--dry-run", action="store_true")
    return parser.parse_known_args(argv)


def main(argv: Optional[Sequence[str]] = None) -> int:
    args, passthrough = parse_args(argv)
    target = (
        sequential_root().parents[1]
        / "src/SystemComponents/Agentic_Framework/03_TreatmentTargetIdentification/01_prepare_targets_from_impact.py"
    )

    output_root = Path(args.output_root).expanduser().resolve()
    output_root.mkdir(parents=True, exist_ok=True)

    script_args = [
        "--impact-root",
        str(Path(args.impact_root).expanduser().resolve()),
        "--output-root",
        str(output_root),
        "--readiness-root",
        str(Path(args.readiness_root).expanduser().resolve()),
        "--network-root",
        str(Path(args.network_root).expanduser().resolve()),
        "--initial-model-runs-root",
        str(Path(args.initial_model_runs_root).expanduser().resolve()),
        "--free-text-root",
        str(Path(args.free_text_root).expanduser().resolve()),
        "--mapping-ranks-csv",
        str(Path(args.mapping_ranks_csv).expanduser().resolve()),
        "--hyde-dense-profiles-csv",
        str(Path(args.hyde_dense_profiles_csv).expanduser().resolve()),
        "--hyde-runs-root",
        str(Path(args.hyde_runs_root).expanduser().resolve()),
        "--predictor-list-path",
        str(Path(args.predictor_list_path).expanduser().resolve()),
        "--predictor-feasibility-csv",
        str(Path(args.predictor_feasibility_csv).expanduser().resolve()),
        "--pattern",
        str(args.pattern),
        "--max-profiles",
        str(int(args.max_profiles)),
        "--top-k",
        str(int(args.top_k)),
        "--min-impact",
        str(float(args.min_impact)),
        "--max-candidate-predictors",
        str(int(args.max_candidate_predictors)),
        "--llm-model",
        str(args.llm_model),
        "--prompt-budget-tokens",
        str(int(args.prompt_budget_tokens)),
        "--critic-max-iterations",
        str(int(args.critic_max_iterations)),
        "--critic-pass-threshold",
        str(float(args.critic_pass_threshold)),
        "--preferred-predictor-count",
        str(int(args.preferred_predictor_count)),
        "--preferred-criterion-count",
        str(int(args.preferred_criterion_count)),
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
        step_label="Step 06 - Target Identification + Updated Model",
        script_path=target,
        script_args=script_args,
        dry_run=bool(args.dry_run),
    )


if __name__ == "__main__":
    raise SystemExit(main())
