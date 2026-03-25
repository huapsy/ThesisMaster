#!/usr/bin/env python3
from __future__ import annotations

import argparse
import datetime as dt
import sys
from pathlib import Path
from typing import Optional, Sequence

THIS_DIR = Path(__file__).resolve().parent
SEQUENTIAL_ROOT = THIS_DIR.parent
if str(SEQUENTIAL_ROOT) not in sys.path:
    sys.path.insert(0, str(SEQUENTIAL_ROOT))

from utils.common import default_python_executable, run_python_script, sequential_root


def _default_hyde_dense_profiles_path() -> Path:
    runs_root = (
        sequential_root().parents[1]
        / "src/backend/utils/agentic_core/others/initial_observation_model_assets/helpers/00_HyDe_based_predictor_ranks/runs"
    )
    candidates = sorted(runs_root.glob("*/dense_profiles.csv"))
    if candidates:
        return candidates[-1]
    return runs_root / "2026-01-15_19-51-47/dense_profiles.csv"


def parse_args(argv: Optional[Sequence[str]] = None) -> tuple[argparse.Namespace, list[str]]:
    root = sequential_root()
    repo = root.parents[1]
    parser = argparse.ArgumentParser(description="Step 02: construct initial observation model.")
    parser.add_argument("--python-exe", type=str, default=default_python_executable())
    parser.add_argument(
        "--mapped-criterions-path",
        type=str,
        default=str(root / "01_operationalization/outputs/mapped_criterions.csv"),
    )
    parser.add_argument("--hyde-dense-profiles-path", type=str, default=str(_default_hyde_dense_profiles_path()))
    parser.add_argument(
        "--llm-mapping-ranks-path",
        type=str,
        default=str(
            sequential_root().parents[1]
            / "src/backend/utils/agentic_core/others/initial_observation_model_assets/helpers/00_LLM_based_mapping_based_predictor_ranks/all_pseudoprofiles__predictor_ranks_dense.csv"
        ),
    )
    parser.add_argument(
        "--ontology-path",
        type=str,
        default=str(
            repo
            / "src/backend/utils/official/ontology_mappings/CRITERION/predictor_to_criterion/input_lists/predictors_list.txt"
        ),
    )
    parser.add_argument(
        "--predictor-feasibility-csv",
        type=str,
        default=str(
            repo / "src/backend/utils/official/multi_dimensional_feasibility_evaluation/PREDICTORS/results/summary/predictor_rankings.csv"
        ),
    )
    parser.add_argument(
        "--results-dir",
        type=str,
        default=str(root / "02_initial_observation_model/outputs"),
    )
    parser.add_argument(
        "--run-id",
        type=str,
        default=dt.datetime.now().strftime("sequential_step02_%Y%m%d_%H%M%S"),
    )
    parser.add_argument("--pseudoprofile-id", type=str, default="")
    parser.add_argument("--llm-model", type=str, default="gpt-5-nano")
    parser.add_argument("--prompt-budget-tokens", type=int, default=400000)
    parser.add_argument("--critic-max-iterations", type=int, default=2)
    parser.add_argument("--critic-pass-threshold", type=float, default=0.74)
    parser.add_argument("--max-workers", type=int, default=12)
    parser.add_argument("--hard-ontology-constraint", action=argparse.BooleanOptionalAction, default=False)
    parser.add_argument("--enable-sampling", action=argparse.BooleanOptionalAction, default=False)
    parser.add_argument("--dry-run", action="store_true")
    return parser.parse_known_args(argv)


def main(argv: Optional[Sequence[str]] = None) -> int:
    args, passthrough = parse_args(argv)
    target = (
        sequential_root().parents[1]
        / "src/backend/SystemComponents/Agentic_Framework/02_ConstructionInitialObservationModel/utils/01_construct_observation_model.py"
    )

    results_dir = Path(args.results_dir).expanduser().resolve()
    results_dir.mkdir(parents=True, exist_ok=True)

    script_args = [
        "--mapped_criterions_path",
        str(Path(args.mapped_criterions_path).expanduser().resolve()),
        "--hyde_dense_profiles_path",
        str(Path(args.hyde_dense_profiles_path).expanduser().resolve()),
        "--llm_mapping_ranks_path",
        str(Path(args.llm_mapping_ranks_path).expanduser().resolve()),
        "--ontology_path",
        str(Path(args.ontology_path).expanduser().resolve()),
        "--predictor_feasibility_csv",
        str(Path(args.predictor_feasibility_csv).expanduser().resolve()),
        "--results_dir",
        str(results_dir),
        "--run_id",
        str(args.run_id),
        "--llm_model",
        str(args.llm_model),
        "--prompt_budget_tokens",
        str(int(args.prompt_budget_tokens)),
        "--critic_max_iterations",
        str(int(args.critic_max_iterations)),
        "--critic_pass_threshold",
        str(float(args.critic_pass_threshold)),
        "--max_workers",
        str(int(args.max_workers)),
    ]
    if args.pseudoprofile_id.strip():
        script_args.extend(["--pseudoprofile_id", args.pseudoprofile_id.strip()])
    if bool(args.hard_ontology_constraint):
        script_args.append("--hard_ontology_constraint")
    if bool(args.enable_sampling):
        script_args.append("--enable_sampling")
    else:
        script_args.append("--no-enable_sampling")
    script_args.extend(passthrough)

    return run_python_script(
        step_label="Step 02 - Initial Observation Model",
        script_path=target,
        script_args=script_args,
        dry_run=bool(args.dry_run),
    )


if __name__ == "__main__":
    raise SystemExit(main())
