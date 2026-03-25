from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, Sequence

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import scipy.stats as stats

from .shared_stats import PALETTE, fit_crossed_mixedlm, p_to_stars, save_figure, violin_with_scatter
from .survey_paths import data_file, ensure_study_dirs


@dataclass(frozen=True)
class RankingStudyConfig:
    study_slug: str
    title: str
    report_name: str
    data_filename: str
    task_col: str
    footrule_col: str
    comparator_label: str
    lower_is_better: bool = True


def _fit_primary_model(summary: pd.DataFrame, *, task_col: str, estimator_col: str, outcome_col: str) -> Dict[str, Any]:
    work = summary.copy()
    work["estimator_bin"] = (work[estimator_col].astype(str) == "phoenix").astype(int)
    if "shift_regime" in work.columns and work["shift_regime"].nunique() > 1:
        formula = f"{outcome_col} ~ estimator_bin + C(shift_regime)"
    else:
        formula = f"{outcome_col} ~ estimator_bin"
    result = fit_crossed_mixedlm(
        work,
        formula=formula,
        effect_term="estimator_bin",
        candidates=[
            {
                "label": "Crossed LME (participant intercept + estimator slope, task intercept)",
                "group_col": "participant_ID",
                "re_formula": "~estimator_bin",
                "variance_components": {"task": task_col},
            },
            {
                "label": "Crossed LME (participant intercept, task intercept)",
                "group_col": "participant_ID",
                "variance_components": {"task": task_col},
            },
            {
                "label": "Crossed LME (task intercept, participant intercept)",
                "group_col": task_col,
                "variance_components": {"participant": "participant_ID"},
            },
        ],
    )
    if result["method"] != "No converged mixed model":
        return result
    phoenix_vals = work.loc[work[estimator_col].astype(str) == "phoenix", outcome_col].to_numpy()
    comp_vals = work.loc[work[estimator_col].astype(str) != "phoenix", outcome_col].to_numpy()
    stat, p_val = stats.mannwhitneyu(phoenix_vals, comp_vals, alternative="two-sided")
    diff = float(np.mean(phoenix_vals) - np.mean(comp_vals))
    return {
        "method": "Mann-Whitney fallback",
        "coefficient": diff,
        "se": 0.0,
        "ci_lower": diff,
        "ci_upper": diff,
        "p_value": float(p_val),
        "statistic": float(stat),
        "error": result.get("error", "No converged mixed model."),
        "shapiro_w": np.nan,
        "shapiro_p": np.nan,
    }


def _model_structure_note(method: str) -> str:
    if method.startswith("Crossed LME"):
        return "participant-level repeated measures with crossed task variability"
    return "fallback comparison after mixed-model convergence issues"


def run_ranking_study(config: RankingStudyConfig) -> None:
    paths = ensure_study_dirs(config.study_slug)
    df = pd.read_csv(data_file(config.data_filename))
    estimator_col = "estimator"
    grouping_cols = ["participant_ID", config.task_col, estimator_col]
    if "shift_regime" in df.columns:
        grouping_cols.append("shift_regime")
    summary = df.groupby(grouping_cols, as_index=False)[config.footrule_col].first()

    phoenix = summary.loc[summary[estimator_col].astype(str) == "phoenix", config.footrule_col].astype(float).to_numpy()
    comparator = summary.loc[summary[estimator_col].astype(str) != "phoenix", config.footrule_col].astype(float).to_numpy()
    model_result = _fit_primary_model(
        summary,
        task_col=config.task_col,
        estimator_col=estimator_col,
        outcome_col=config.footrule_col,
    )

    direction_text = "lower is better" if config.lower_is_better else "higher is better"
    report_lines = [
        "=" * 68,
        config.title,
        f"Primary model follows the protocol-level mixed-effects comparison with participant-level repeated measures and task-level crossed random effects; {direction_text}.",
        "=" * 68,
        f"Method: {model_result['method']}",
        f"Model structure: {_model_structure_note(model_result['method'])}",
        f"PHOENIX - {config.comparator_label} coefficient: {model_result['coefficient']:.4f}",
        f"p-value: {model_result['p_value']:.4f} ({p_to_stars(model_result['p_value'])})",
    ]
    if not np.isnan(model_result["shapiro_w"]):
        report_lines.append(
            f"Residual Shapiro-Wilk: W={model_result['shapiro_w']:.4f}, p={model_result['shapiro_p']:.4f}"
        )
    report_lines.extend(
        [
            "",
            f"PHOENIX mean={np.mean(phoenix):.3f}, SD={np.std(phoenix, ddof=1):.3f}, n={len(phoenix)}",
            f"{config.comparator_label} mean={np.mean(comparator):.3f}, SD={np.std(comparator, ddof=1):.3f}, n={len(comparator)}",
        ]
    )
    if "shift_regime" in summary.columns:
        report_lines.append("")
        report_lines.append("Shift-regime deltas (PHOENIX - comparator):")
        regime_table = (
            summary.groupby(["shift_regime", estimator_col], as_index=False)[config.footrule_col]
            .mean()
            .pivot(index="shift_regime", columns=estimator_col, values=config.footrule_col)
        )
        if {"phoenix"}.issubset(regime_table.columns):
            comparator_cols = [col for col in regime_table.columns if col != "phoenix"]
            if comparator_cols:
                comparator_col = comparator_cols[0]
                for regime_name, row in regime_table.iterrows():
                    report_lines.append(f"  {regime_name}: {float(row['phoenix'] - row[comparator_col]):.3f}")
    (paths["report_dir"] / config.report_name).write_text("\n".join(report_lines), encoding="utf-8")

    fig, ax = plt.subplots(figsize=(9, 5.5))
    violin_with_scatter(
        ax,
        {"PHOENIX": phoenix, config.comparator_label: comparator},
        title=config.title,
        ylabel=config.footrule_col.replace("_", " ").title(),
        colors=[PALETTE["primary"], PALETTE["secondary"]],
        adj_p=model_result["p_value"],
        ref_line=0.0 if config.lower_is_better else None,
        ref_label="Perfect match" if config.lower_is_better else None,
    )
    plt.tight_layout()
    save_figure(fig, paths["visuals_dir"] / f"{config.study_slug}_violin.png")

    tasks = sorted(summary[config.task_col].astype(str).unique().tolist())
    x = np.arange(len(tasks))
    width = 0.35
    fig2, ax2 = plt.subplots(figsize=(max(10, 1.0 * len(tasks) + 3), 5.5))
    for offset, est, color, label in [
        (-width / 2, "phoenix", PALETTE["primary"], "PHOENIX"),
        (width / 2, [item for item in summary[estimator_col].astype(str).unique().tolist() if item != "phoenix"][0], PALETTE["secondary"], config.comparator_label),
    ]:
        vals_per_task = [
            summary.loc[
                (summary[config.task_col].astype(str) == task) & (summary[estimator_col].astype(str) == est),
                config.footrule_col,
            ].astype(float).to_numpy()
            for task in tasks
        ]
        means = [float(np.mean(vals)) if len(vals) else 0.0 for vals in vals_per_task]
        sds = [float(np.std(vals, ddof=1)) if len(vals) > 1 else 0.0 for vals in vals_per_task]
        ax2.bar(x + offset, means, width=width, yerr=sds, color=color, alpha=0.80, capsize=3, label=label)
    ax2.set_xticks(x)
    ax2.set_xticklabels(tasks, rotation=30, ha="right")
    ax2.set_ylabel(config.footrule_col.replace("_", " ").title())
    ax2.set_title(f"{config.title}: per-task summary")
    ax2.legend()
    plt.tight_layout()
    save_figure(fig2, paths["visuals_dir"] / f"{config.study_slug}_per_task_bar.png")

    if "shift_regime" in summary.columns:
        regime_table = (
            summary.groupby(["shift_regime", estimator_col], as_index=False)[config.footrule_col]
            .mean()
            .pivot(index="shift_regime", columns=estimator_col, values=config.footrule_col)
        )
        comparator_cols = [col for col in regime_table.columns if col != "phoenix"]
        if comparator_cols:
            comparator_col = comparator_cols[0]
            delta = regime_table["phoenix"] - regime_table[comparator_col]
            fig3, ax3 = plt.subplots(figsize=(8, 4.5))
            colors = [PALETTE["primary"] if val <= 0 else PALETTE["secondary"] for val in delta.values]
            ax3.bar(delta.index.astype(str), delta.values, color=colors, alpha=0.80)
            ax3.axhline(0, color=PALETTE["neutral"], linestyle="--", linewidth=1.0)
            ax3.set_ylabel("PHOENIX - comparator")
            ax3.set_title(f"{config.title}: shift-regime sensitivity")
            plt.tight_layout()
            save_figure(fig3, paths["visuals_dir"] / f"{config.study_slug}_shift_regime_bar.png")
