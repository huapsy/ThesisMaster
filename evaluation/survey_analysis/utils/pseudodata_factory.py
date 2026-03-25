from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Dict, Sequence

import numpy as np
import pandas as pd

from survey_paths import DATA_DIR


SEED = 42
RNG = np.random.default_rng(SEED)
LIKERT_MIN = 1
LIKERT_MAX = 9


def clip_likert(values: np.ndarray, lo: int = LIKERT_MIN, hi: int = LIKERT_MAX) -> np.ndarray:
    return np.clip(np.round(values), lo, hi).astype(int)


def _save(df: pd.DataFrame, filename: str) -> None:
    path = DATA_DIR / filename
    df.to_csv(path, index=False)
    print(f"  Saved {path} ({len(df)} rows)")


def _task_regime(task_index: int) -> str:
    regimes = ["standard", "ambiguous", "implementation_shift", "context_shift"]
    return regimes[(task_index - 1) % len(regimes)]


def _generate_rank_comparison(
    *,
    filename: str,
    id_label: str,
    estimator_labels: Sequence[str],
    n_participants: int,
    n_tasks: int,
    n_nodes: int,
    footrule_col: str,
) -> pd.DataFrame:
    rows = []
    nodes = [f"node_{i}" for i in range(1, n_nodes + 1)]
    for pid in range(1, n_participants + 1):
        participant_style = RNG.normal(0.0, 0.15)
        for tid in range(1, n_tasks + 1):
            gold = RNG.permutation(n_nodes) + 1
            regime = _task_regime(tid)
            for estimator in estimator_labels:
                perm = gold.copy()
                difficulty_shift = 1 if regime in {"ambiguous", "context_shift"} else 0
                if estimator == "phoenix":
                    n_swaps = RNG.integers(0, 2 + difficulty_shift)
                else:
                    n_swaps = RNG.integers(1 + difficulty_shift, 4 + difficulty_shift)
                for _ in range(n_swaps):
                    i, j = RNG.choice(n_nodes, size=2, replace=False)
                    perm[i], perm[j] = perm[j], perm[i]
                if participant_style > 0.20 and estimator != "phoenix":
                    perm = np.roll(perm, 1)
                footrule = int(np.sum(np.abs(perm - gold)))
                for idx, node in enumerate(nodes):
                    rows.append(
                        {
                            "participant_ID": f"P{pid:03d}",
                            id_label: f"TASK{tid:02d}",
                            "estimator": estimator,
                            "node": node,
                            "rank": int(perm[idx]),
                            footrule_col: footrule,
                            "shift_regime": regime,
                        }
                    )
    df = pd.DataFrame(rows)
    _save(df, filename)
    return df


@dataclass(frozen=True)
class DualSourceStudySpec:
    study_slug: str
    filename: str
    item_col: str
    n_raters: int
    n_items: int
    rater_group: str
    dimension_profiles: Dict[str, Dict[str, float]]


def _generate_dual_source_likert_study(spec: DualSourceStudySpec) -> pd.DataFrame:
    shift_adjustments = {
        "standard": {"hcp": 0.00, "phoenix": 0.00},
        "ambiguous": {"hcp": 0.35, "phoenix": 0.10},
        "implementation_shift": {"hcp": -0.10, "phoenix": 0.40},
        "context_shift": {"hcp": 0.20, "phoenix": 0.30},
    }
    rows = []
    for rater_idx in range(1, spec.n_raters + 1):
        rater_effect = RNG.normal(0.0, 0.35)
        for item_idx in range(1, spec.n_items + 1):
            item_effect = RNG.normal(0.0, 0.30)
            shift_regime = _task_regime(item_idx)
            task_domain = ["sleep", "anxiety", "social", "stress", "mood"][(item_idx - 1) % 5]
            for source in ("hcp", "phoenix"):
                source_item_effect = RNG.normal(0.0, 0.18)
                for dimension, params in spec.dimension_profiles.items():
                    source_mean = params[source]
                    if shift_regime == "ambiguous":
                        source_mean += params.get("ambiguous_bonus_hcp" if source == "hcp" else "ambiguous_bonus_phoenix", 0.0)
                    if shift_regime == "implementation_shift":
                        source_mean += params.get("implementation_bonus_hcp" if source == "hcp" else "implementation_bonus_phoenix", 0.0)
                    if shift_regime == "context_shift":
                        source_mean += params.get("context_bonus_hcp" if source == "hcp" else "context_bonus_phoenix", 0.0)
                    raw = (
                        source_mean
                        + shift_adjustments[shift_regime][source]
                        + rater_effect
                        + item_effect
                        + source_item_effect
                        + RNG.normal(0.0, params.get("sd", 0.80))
                    )
                    rows.append(
                        {
                            "participant_ID": f"{spec.study_slug.upper()}_R{rater_idx:02d}",
                            spec.item_col: f"{spec.study_slug.upper()}_{item_idx:02d}",
                            "source": source,
                            "dimension": dimension,
                            "rating": int(clip_likert(np.array([raw]))[0]),
                            "shift_regime": shift_regime,
                            "task_domain": task_domain,
                            "rater_group": spec.rater_group,
                        }
                    )
    df = pd.DataFrame(rows)
    _save(df, spec.filename)
    return df


def generate_study_00() -> pd.DataFrame:
    return _generate_rank_comparison(
        filename="study_00_momentary_impact.csv",
        id_label="network_ID",
        estimator_labels=("phoenix", "static"),
        n_participants=30,
        n_tasks=10,
        n_nodes=5,
        footrule_col="footrule_distance",
    )


def generate_study_01() -> pd.DataFrame:
    return _generate_dual_source_likert_study(
        DualSourceStudySpec(
            study_slug="study_01",
            filename="study_01_operationalization.csv",
            item_col="text_ID",
            n_raters=5,
            n_items=10,
            rater_group="healthcare_expert",
            dimension_profiles={
                "accurate_depiction": {"hcp": 7.4, "phoenix": 7.0, "sd": 0.75, "ambiguous_bonus_hcp": 0.25},
                "mathematical_suitability": {"hcp": 6.8, "phoenix": 7.3, "sd": 0.70, "implementation_bonus_phoenix": 0.35},
                "data_collection_feasibility": {"hcp": 6.7, "phoenix": 7.1, "sd": 0.85, "context_bonus_phoenix": 0.25},
            },
        )
    )


def generate_study_02() -> pd.DataFrame:
    return _generate_dual_source_likert_study(
        DualSourceStudySpec(
            study_slug="study_02",
            filename="study_02_initial_model.csv",
            item_col="item_ID",
            n_raters=5,
            n_items=10,
            rater_group="healthcare_expert",
            dimension_profiles={
                "accurate_depiction": {"hcp": 7.2, "phoenix": 6.9, "sd": 0.80, "ambiguous_bonus_hcp": 0.20},
                "mathematical_suitability": {"hcp": 6.7, "phoenix": 7.5, "sd": 0.75, "implementation_bonus_phoenix": 0.45},
                "data_collection_feasibility": {"hcp": 6.6, "phoenix": 7.2, "sd": 0.90, "context_bonus_phoenix": 0.25},
                "treatment_translation": {"hcp": 6.8, "phoenix": 7.3, "sd": 0.85, "context_bonus_hcp": 0.15},
            },
        )
    )


def generate_study_03() -> pd.DataFrame:
    df = _generate_rank_comparison(
        filename="study_03_treatment_target.csv",
        id_label="task_ID",
        estimator_labels=("phoenix", "human"),
        n_participants=30,
        n_tasks=10,
        n_nodes=5,
        footrule_col="footrule_vs_gold",
    )
    return df


def generate_study_04() -> pd.DataFrame:
    return _generate_dual_source_likert_study(
        DualSourceStudySpec(
            study_slug="study_04",
            filename="study_04_updated_model.csv",
            item_col="task_ID",
            n_raters=5,
            n_items=10,
            rater_group="healthcare_expert",
            dimension_profiles={
                "accurate_depiction": {"hcp": 7.1, "phoenix": 6.9, "sd": 0.80, "ambiguous_bonus_hcp": 0.20},
                "mathematical_suitability": {"hcp": 6.7, "phoenix": 7.4, "sd": 0.75, "implementation_bonus_phoenix": 0.35},
                "data_collection_feasibility": {"hcp": 6.6, "phoenix": 7.2, "sd": 0.80, "context_bonus_phoenix": 0.20},
                "treatment_translation": {"hcp": 6.9, "phoenix": 7.3, "sd": 0.85, "context_bonus_phoenix": 0.15},
                "bfs_alignment": {"hcp": 6.5, "phoenix": 7.7, "sd": 0.70, "implementation_bonus_phoenix": 0.50},
            },
        )
    )


def generate_study_05() -> pd.DataFrame:
    return _generate_dual_source_likert_study(
        DualSourceStudySpec(
            study_slug="study_05",
            filename="study_05_intervention.csv",
            item_col="intervention_ID",
            n_raters=30,
            n_items=10,
            rater_group="non_expert_user",
            dimension_profiles={
                "overall_congruence": {"hcp": 6.9, "phoenix": 7.1, "sd": 0.80},
                "depth_of_tailoring": {"hcp": 6.6, "phoenix": 7.5, "sd": 0.80, "context_bonus_phoenix": 0.30},
                "actionability": {"hcp": 6.8, "phoenix": 7.4, "sd": 0.75, "implementation_bonus_phoenix": 0.25},
                "professional_tone": {"hcp": 7.4, "phoenix": 7.0, "sd": 0.70, "ambiguous_bonus_hcp": 0.20},
                "predicted_effectiveness": {"hcp": 6.8, "phoenix": 7.3, "sd": 0.85, "context_bonus_phoenix": 0.20},
            },
        )
    )


def generate_study_06(study_frames: Dict[str, pd.DataFrame]) -> pd.DataFrame:
    frame_specs = {
        "study_01": ("text_ID", study_frames["study_01"]),
        "study_02": ("item_ID", study_frames["study_02"]),
        "study_04": ("task_ID", study_frames["study_04"]),
        "study_05": ("intervention_ID", study_frames["study_05"]),
    }
    rows = []
    for study_id, (task_col, frame) in frame_specs.items():
        for _, row in frame.iterrows():
            rows.append(
                {
                    "study_id": study_id,
                    "dimension": str(row["dimension"]),
                    "reasoner_group": str(row["source"]),
                    "normalized_score": round((float(row["rating"]) - LIKERT_MIN) / (LIKERT_MAX - LIKERT_MIN), 4),
                    "task_key": f"{study_id}:{row[task_col]}",
                    "participant_ID": str(row["participant_ID"]),
                    "shift_regime": str(row.get("shift_regime", "standard")),
                    "rater_group": str(row.get("rater_group", "")),
                }
            )
    df = pd.DataFrame(rows)
    _save(df, "study_06_holistic.csv")
    return df


def generate_all_studies() -> None:
    print("Generating pseudodata for all studies …")
    generate_study_00()
    study_01 = generate_study_01()
    study_02 = generate_study_02()
    generate_study_03()
    study_04 = generate_study_04()
    study_05 = generate_study_05()
    generate_study_06(
        {
            "study_01": study_01,
            "study_02": study_02,
            "study_04": study_04,
            "study_05": study_05,
        }
    )
    print("\nAll pseudodata files generated successfully.")
