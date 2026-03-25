from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import scipy.stats as stats

from shared_stats import PALETTE, fit_crossed_mixedlm, forest_plot, p_to_stars, save_figure
from survey_paths import data_file, ensure_study_dirs


@dataclass(frozen=True)
class HolisticStudyConfig:
    study_slug: str
    title: str
    report_name: str
    data_filename: str


def _display_label(value: str) -> str:
    return str(value).replace("_", " ").title()


def _holm_correct(p_values: list[float]) -> list[float]:
    indexed = sorted(enumerate(p_values), key=lambda item: item[1])
    adjusted = [1.0] * len(p_values)
    running_max = 0.0
    n_tests = len(p_values)
    for rank, (original_idx, p_value) in enumerate(indexed, start=1):
        scaled = (n_tests - rank + 1) * p_value
        running_max = max(running_max, scaled)
        adjusted[original_idx] = min(running_max, 1.0)
    return adjusted


def run_holistic_reasoner_comparison(config: HolisticStudyConfig) -> None:
    paths = ensure_study_dirs(config.study_slug)
    df = pd.read_csv(data_file(config.data_filename))
    studies = sorted(df["study_id"].astype(str).unique().tolist())

    report_lines = [
        "=" * 72,
        config.title,
        "Human-in-the-loop comparison focused on PHOENIX vs healthcare expert outputs",
        "=" * 72,
    ]

    work = df.copy()
    work["reasoner_bin"] = (work["reasoner_group"].astype(str) == "phoenix").astype(int)
    formula_terms = ["reasoner_bin", "C(study_id)", "C(dimension)"]
    if "shift_regime" in work.columns and work["shift_regime"].nunique() > 1:
        formula_terms.append("C(shift_regime)")
    unified_result = fit_crossed_mixedlm(
        work,
        formula="normalized_score ~ " + " + ".join(formula_terms),
        effect_term="reasoner_bin",
        candidates=[
            {
                "label": "Crossed LME (participant intercept + reasoner slope, task intercept, answer-block intercept)",
                "group_col": "participant_ID",
                "re_formula": "~reasoner_bin",
                "variance_components": {"task": "task_key", "answer_block": "response_run_id"},
            },
            {
                "label": "Crossed LME (participant intercept, task intercept, answer-block intercept)",
                "group_col": "participant_ID",
                "variance_components": {"task": "task_key", "answer_block": "response_run_id"},
            },
            {
                "label": "Crossed LME (task intercept, participant intercept)",
                "group_col": "task_key",
                "variance_components": {"participant": "participant_ID"},
            },
        ],
    )
    if unified_result["method"] != "No converged mixed model":
        report_lines.extend(
            [
                "",
                "--- Unified mixed model ---",
                f"Method: {unified_result['method']}",
                f"PHOENIX - HCP coefficient: {unified_result['coefficient']:.4f}",
                f"95% CI: [{unified_result['ci_lower']:.4f}, {unified_result['ci_upper']:.4f}]",
                f"p-value: {unified_result['p_value']:.4f} ({p_to_stars(unified_result['p_value'])})",
                "Primary estimand adjusts for study and dimension while accounting for participant severity, task difficulty, and participant-specific answer-block clustering.",
            ]
        )
        if not np.isnan(unified_result.get("shapiro_w", np.nan)):
            report_lines.append(
                f"Residual Shapiro-Wilk: W={unified_result['shapiro_w']:.4f}, p={unified_result['shapiro_p']:.4f}"
            )
    else:
        phoenix_vals = work.loc[work["reasoner_group"].astype(str) == "phoenix", "normalized_score"].to_numpy()
        hcp_vals = work.loc[work["reasoner_group"].astype(str) == "hcp", "normalized_score"].to_numpy()
        stat, p_val = stats.mannwhitneyu(phoenix_vals, hcp_vals, alternative="two-sided")
        report_lines.extend(
            [
                "",
                "--- Unified mixed model ---",
                "Method: Mann-Whitney fallback",
                f"U-statistic: {float(stat):.4f}",
                f"p-value: {float(p_val):.4f}",
                f"Fallback reason: {unified_result.get('error', 'No converged mixed model.')}",
            ]
        )

    study_effects: Dict[str, Dict[str, Any]] = {}
    raw_study_p_values = []
    for study_id in studies:
        sub = work.loc[work["study_id"].astype(str) == study_id].copy()
        phoenix_vals = sub.loc[sub["reasoner_group"].astype(str) == "phoenix", "normalized_score"].to_numpy()
        hcp_vals = sub.loc[sub["reasoner_group"].astype(str) == "hcp", "normalized_score"].to_numpy()
        diff = float(np.mean(phoenix_vals) - np.mean(hcp_vals))
        result = fit_crossed_mixedlm(
            sub,
            formula="normalized_score ~ reasoner_bin",
            effect_term="reasoner_bin",
            candidates=[
                {
                    "label": "Crossed LME (participant intercept + reasoner slope, task intercept, answer-block intercept)",
                    "group_col": "participant_ID",
                    "re_formula": "~reasoner_bin",
                    "variance_components": {"task": "task_key", "answer_block": "response_run_id"},
                },
                {
                    "label": "Crossed LME (participant intercept, task intercept, answer-block intercept)",
                    "group_col": "participant_ID",
                    "variance_components": {"task": "task_key", "answer_block": "response_run_id"},
                },
                {
                    "label": "Crossed LME (task intercept, participant intercept)",
                    "group_col": "task_key",
                    "variance_components": {"participant": "participant_ID"},
                },
            ],
        )
        if result["method"] == "No converged mixed model":
            stat, p_val = stats.mannwhitneyu(phoenix_vals, hcp_vals, alternative="two-sided")
            coef = diff
            ci_lo = diff
            ci_hi = diff
            method = "Mann-Whitney fallback"
        else:
            coef = float(result["coefficient"])
            ci_lo = float(result["ci_lower"])
            ci_hi = float(result["ci_upper"])
            p_val = float(result["p_value"])
            method = result["method"]
        study_effects[study_id] = {
            "coef": coef,
            "ci_lo": ci_lo,
            "ci_hi": ci_hi,
            "p_value": p_val,
            "method": method,
        }
        raw_study_p_values.append(p_val)

    corrected_study_p_values = _holm_correct(raw_study_p_values)
    report_lines.append("")
    report_lines.append("--- Study-specific follow-up models ---")
    report_lines.append("Secondary study-level contrasts are Holm-adjusted across studies.")
    for study_id, corrected_p in zip(studies, corrected_study_p_values):
        study_effects[study_id]["p_value_holm"] = corrected_p
        report_lines.extend(
            [
                "",
                f"Study: {study_id}",
                f"  HCP mean={np.mean(work.loc[(work['study_id'].astype(str) == study_id) & (work['reasoner_group'].astype(str) == 'hcp'), 'normalized_score'].to_numpy()):.4f}, PHOENIX mean={np.mean(work.loc[(work['study_id'].astype(str) == study_id) & (work['reasoner_group'].astype(str) == 'phoenix'), 'normalized_score'].to_numpy()):.4f}",
                f"  PHOENIX - HCP={study_effects[study_id]['coef']:.4f}",
                f"  95% CI: [{study_effects[study_id]['ci_lo']:.4f}, {study_effects[study_id]['ci_hi']:.4f}]",
                f"  p-value (raw)={study_effects[study_id]['p_value']:.4f}, p-value (Holm)={corrected_p:.4f} ({p_to_stars(corrected_p)})",
                f"  Method={study_effects[study_id]['method']}",
            ]
        )

    report_path = paths["report_dir"] / config.report_name
    report_path.write_text("\n".join(report_lines), encoding="utf-8")

    order = studies
    fig, axes = plt.subplots(1, len(order), figsize=(max(7, 4 * len(order)), 5.0), sharey=True)
    if len(order) == 1:
        axes = [axes]
    rng = np.random.default_rng(42)
    for ax, study_id in zip(axes, order):
        sub = work.loc[work["study_id"].astype(str) == study_id].copy()
        positions = [1, 2]
        hcp_vals = sub.loc[sub["reasoner_group"].astype(str) == "hcp", "normalized_score"].to_numpy()
        phoenix_vals = sub.loc[sub["reasoner_group"].astype(str) == "phoenix", "normalized_score"].to_numpy()
        violin = ax.violinplot([hcp_vals, phoenix_vals], positions=positions, showmedians=True, showextrema=False)
        for body, color in zip(violin["bodies"], [PALETTE["secondary"], PALETTE["primary"]]):
            body.set_facecolor(color)
            body.set_alpha(0.35)
        for vals, pos, color in [(hcp_vals, 1, PALETTE["secondary"]), (phoenix_vals, 2, PALETTE["primary"])]:
            jitter = rng.uniform(-0.08, 0.08, size=len(vals))
            ax.scatter(pos + jitter, vals, color=color, alpha=0.35, s=12, zorder=3)
        ax.axhline(0.5, color=PALETTE["neutral"], linestyle="--", linewidth=1.0)
        ax.set_xticks(positions)
        ax.set_xticklabels(["HCP", "PHX"])
        ax.set_title(_display_label(study_id))
        ax.set_ylim(-0.05, 1.05)
    axes[0].set_ylabel("Normalized score")
    fig.suptitle(config.title, fontsize=13, y=1.02)
    plt.tight_layout()
    save_figure(fig, paths["visuals_dir"] / f"{config.study_slug}_reasoner_violin.png")

    delta_table = (
        work.groupby(["study_id", "dimension", "reasoner_group"], as_index=False)["normalized_score"]
        .mean()
        .pivot_table(index=["study_id", "dimension"], columns="reasoner_group", values="normalized_score")
        .reset_index()
    )
    if {"hcp", "phoenix"}.issubset(delta_table.columns):
        delta_table["phoenix_minus_hcp"] = delta_table["phoenix"] - delta_table["hcp"]
        heatmap_table = delta_table.pivot(index="dimension", columns="study_id", values="phoenix_minus_hcp")
        fig2, ax2 = plt.subplots(figsize=(max(7, 1.8 * len(heatmap_table.columns)), max(4, 0.6 * len(heatmap_table.index) + 1.5)))
        im = ax2.imshow(heatmap_table.values, cmap="RdBu_r", aspect="auto")
        ax2.set_xticks(np.arange(len(heatmap_table.columns)))
        ax2.set_xticklabels([_display_label(c) for c in heatmap_table.columns], rotation=20, ha="right")
        ax2.set_yticks(np.arange(len(heatmap_table.index)))
        ax2.set_yticklabels([_display_label(r) for r in heatmap_table.index])
        ax2.set_title("PHOENIX - HCP normalized score by study and dimension")
        for i in range(heatmap_table.shape[0]):
            for j in range(heatmap_table.shape[1]):
                ax2.text(j, i, f"{heatmap_table.iloc[i, j]:.2f}", ha="center", va="center", fontsize=8)
        plt.colorbar(im, ax=ax2, label="Delta")
        plt.tight_layout()
        save_figure(fig2, paths["visuals_dir"] / f"{config.study_slug}_dimension_heatmap.png")

    fig3, ax3 = plt.subplots(figsize=(8, max(4, 0.8 * len(order) + 1.2)))
    forest_plot(
        ax3,
        dimensions=[_display_label(study_id) for study_id in order],
        effects=[study_effects[study_id]["coef"] for study_id in order],
        ci_lowers=[study_effects[study_id]["ci_lo"] for study_id in order],
        ci_uppers=[study_effects[study_id]["ci_hi"] for study_id in order],
        title="Holistic PHOENIX - HCP effect by study",
        xlabel="Normalized score difference",
        ref_line=0.0,
    )
    plt.tight_layout()
    save_figure(fig3, paths["visuals_dir"] / f"{config.study_slug}_study_forest.png")
