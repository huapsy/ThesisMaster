#!/usr/bin/env python3
"""
Generate publication-style figures and CSV tables for the PHOENIX example run.
"""

from __future__ import annotations

import argparse
import json
import shutil
import time
import textwrap
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional, Sequence

import matplotlib

matplotlib.use("Agg")

import matplotlib.gridspec as gridspec
import matplotlib.patches as mpatches
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd


REPO_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_RUN_ROOT = REPO_ROOT / "evaluation/integrated_pipeline/runs/example_run_2026_report_ready"
DEFAULT_PROFILE_ID = "pseudoprofile_FTC_ID200"
DEFAULT_OUT_FIGS = Path(__file__).parent / "assets/figures"
DEFAULT_OUT_TABLES = Path(__file__).parent / "assets/tables"
ARCHITECTURE_SOURCE = REPO_ROOT / "src/backend/overview/create_flowchart.png"


plt.rcParams.update(
    {
        "font.family": "DejaVu Sans",
        "font.size": 9,
        "axes.titlesize": 10,
        "axes.labelsize": 9,
        "xtick.labelsize": 8,
        "ytick.labelsize": 8,
        "figure.dpi": 150,
        "savefig.dpi": 220,
        "axes.spines.top": False,
        "axes.spines.right": False,
        "axes.grid": True,
        "grid.alpha": 0.22,
        "grid.linestyle": "--",
    }
)


C_BLUE = "#1D4ED8"
C_TEAL = "#0E7490"
C_GREEN = "#047857"
C_AMBER = "#B45309"
C_PURPLE = "#6D28D9"
C_RED = "#DC2626"
C_GREY = "#475569"
C_LIGHT = "#F8FAFC"
C_BORDER = "#CBD5E1"
DPI = 220


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Generate PHOENIX example figures and tables.")
    parser.add_argument("--run-root", type=str, default=str(DEFAULT_RUN_ROOT))
    parser.add_argument("--profile-id", type=str, default=DEFAULT_PROFILE_ID)
    parser.add_argument("--figures-dir", type=str, default=str(DEFAULT_OUT_FIGS))
    parser.add_argument("--tables-dir", type=str, default=str(DEFAULT_OUT_TABLES))
    parser.add_argument("--timing-root", action="append", default=[], help="Additional run roots for component timing aggregation.")
    return parser.parse_args()


def _safe_float(value: Any, default: float = 0.0) -> float:
    if value is None:
        return default
    if isinstance(value, (int, float)):
        if pd.isna(value):
            return default
        return float(value)
    text = str(value).strip()
    if not text:
        return default
    try:
        return float(text.replace(",", "."))
    except Exception:
        return default


def _load_json(path: Path) -> Dict[str, Any]:
    if not path.exists():
        return {}
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return {}


def _load_csv(path: Path, **kwargs: Any) -> pd.DataFrame:
    if not path.exists():
        return pd.DataFrame()
    kwargs = dict(kwargs)
    for sep in [kwargs.pop("sep", None), ",", ";", "\t", "|"]:
        if sep is None:
            continue
        try:
            frame = pd.read_csv(path, sep=sep, **kwargs)
            if frame.shape[1] > 1 or sep == ",":
                return frame
        except Exception:
            continue
    try:
        return pd.read_csv(path, **kwargs)
    except Exception:
        return pd.DataFrame()


def _save(fig: plt.Figure, out_dir: Path, name: str) -> Path:
    path = out_dir / f"{name}.png"
    fig.savefig(path, dpi=DPI, bbox_inches="tight", facecolor="white")
    plt.close(fig)
    print(f"  [saved] {path.name}")
    return path


def _write_csv(frame: pd.DataFrame, out_dir: Path, name: str) -> Optional[Path]:
    if frame.empty:
        return None
    path = out_dir / f"{name}.csv"
    frame.to_csv(path, index=False)
    print(f"  [saved] {path.name}")
    return path


def _shorten(text: Any, limit: int = 48) -> str:
    raw = str(text or "").strip()
    if len(raw) <= limit:
        return raw
    return raw[: limit - 1] + "..."


def _wrap(text: Any, width: int = 30) -> str:
    raw = str(text or "").strip()
    if not raw:
        return ""
    return textwrap.fill(raw, width=max(12, int(width)))


def _shorten_path(text: Any, keep: int = 3, limit: int = 70) -> str:
    raw = str(text or "").strip()
    if not raw:
        return ""
    token = " / ".join([part.strip() for part in raw.split(" / ") if part.strip()][-keep:])
    return _shorten(token, limit=limit)


def _latest_step02_profile_dir(run_root: Path, profile_id: str) -> Optional[Path]:
    model_root = run_root / "01_initial_observation_model" / "runs"
    if not model_root.exists():
        return None
    matches = sorted(model_root.glob(f"*/profiles/{profile_id}"))
    if not matches:
        return None
    return matches[-1]


def _load_step02_model(run_root: Path, profile_id: str) -> Dict[str, Any]:
    profile_dir = _latest_step02_profile_dir(run_root, profile_id)
    if profile_dir is None:
        return {}
    final_payload = _load_json(profile_dir / "llm_observation_model_final.json")
    if final_payload:
        return final_payload
    return _load_json(profile_dir / "llm_observation_model_raw.json")


def _copy_architecture_figure(out_dir: Path) -> Optional[Path]:
    if not ARCHITECTURE_SOURCE.exists():
        return None
    target = out_dir / "fig_00_phoenix_architecture.png"
    shutil.copy2(ARCHITECTURE_SOURCE, target)
    print(f"  [copied] {target.name}")
    return target


def _copy_native_pipeline_visuals(run_root: Path, out_dir: Path) -> List[Path]:
    native_roots = [
        run_root / "04_time_series_analysis",
        run_root / "05_momentary_impact_coefficients",
        run_root / "07_hapa_digital_intervention",
        run_root / "09_impact_visualizations",
    ]
    copied: List[Path] = []
    seen_sources: set[str] = set()
    max_files = 24
    allowed_suffixes = {".png", ".jpg", ".jpeg", ".svg"}

    for native_root in native_roots:
        if not native_root.exists():
            continue
        for source in sorted(native_root.rglob("*")):
            if not source.is_file() or source.suffix.lower() not in allowed_suffixes:
                continue
            source_key = str(source.resolve())
            if source_key in seen_sources:
                continue
            seen_sources.add(source_key)
            stage_token = native_root.name.replace("_", "-")
            target_name = f"fig_native_{stage_token}_{source.stem}{source.suffix.lower()}"
            target = out_dir / target_name
            try:
                shutil.copy2(source, target)
            except Exception:
                continue
            copied.append(target)
            print(f"  [copied] {target.name}")
            if len(copied) >= max_files:
                return copied
    return copied


def _table_figure(
    frame: pd.DataFrame,
    *,
    title: str,
    header_color: str,
    zebra_color: str,
    out_dir: Path,
    name: str,
    font_size: float = 8.0,
    row_scale: float = 1.55,
) -> Optional[Path]:
    if frame.empty:
        return None
    fig_height = max(2.6, 0.52 * len(frame) + 1.6)
    fig, ax = plt.subplots(figsize=(12, fig_height))
    ax.axis("off")
    table = ax.table(cellText=frame.values, colLabels=frame.columns, loc="center", cellLoc="left")
    table.auto_set_font_size(False)
    table.set_fontsize(float(font_size))
    table.scale(1.0, float(row_scale))
    for (row, col), cell in table.get_celld().items():
        cell.get_text().set_wrap(True)
        if row == 0:
            cell.set_facecolor(header_color)
            cell.set_text_props(color="white", fontweight="bold")
        elif row % 2 == 0:
            cell.set_facecolor(zebra_color)
        cell.set_edgecolor(C_BORDER)
    ax.set_title(title, fontsize=10, fontweight="bold", pad=10)
    return _save(fig, out_dir, name)


def fig_step01(run_root: Path, profile_id: str, out_figs: Path, out_tables: Path) -> None:
    print("\n[Step 01] Operationalization")
    frame = _load_csv(run_root / "00_operationalization/outputs/mapped_criterions.csv", low_memory=False)
    if frame.empty:
        print("  [warn] mapped_criterions.csv missing.")
        return
    if "pseudoprofile_id" in frame.columns:
        frame = frame[frame["pseudoprofile_id"].astype(str) == profile_id].copy()
    if frame.empty:
        print("  [warn] no Step-01 rows for profile.")
        return

    display = pd.DataFrame(
        {
            "Criterion ID": frame.get("variable_id", pd.Series(dtype=str)).astype(str),
            "Criterion Label": frame.get("variable_label", pd.Series(dtype=str)).map(lambda value: _wrap(_shorten(value, 72), 34)),
            "Mapped Leaf": frame.get("chosen_leaf_full_path", pd.Series(dtype=str)).map(lambda value: _wrap(_shorten_path(value, keep=3, limit=56), 32)),
            "Confidence": frame.get("chosen_confidence", pd.Series(dtype=float)).map(lambda value: f"{_safe_float(value):.2f}"),
            "Severity": frame.get("variable_severity_0_1", pd.Series(dtype=float)).map(lambda value: f"{_safe_float(value):.2f}"),
        }
    ).head(10)
    _write_csv(display, out_tables, "table_01_step01_mapped_criteria")
    _table_figure(
        display,
        title="Step 01 - Operationalized complaint criteria and ontology leaves",
        header_color=C_BLUE,
        zebra_color="#F0F4FF",
        out_dir=out_figs,
        name="fig_01a_step01_mapped_criteria",
        font_size=6.6,
        row_scale=1.50,
    )

    if {"variable_id", "variable_label", "chosen_confidence"}.issubset(frame.columns):
        sub = frame[["variable_id", "variable_label", "chosen_confidence"]].copy().head(10)
        labels = [(f"{row.variable_id}: {_shorten(row.variable_label, 28)}") for row in sub.itertuples(index=False)]
        values = [_safe_float(value) for value in sub["chosen_confidence"].tolist()]
        fig, ax = plt.subplots(figsize=(9.2, max(4.0, 0.52 * len(labels) + 1.0)))
        bars = ax.barh(range(len(labels)), values, color=C_BLUE, alpha=0.85, height=0.62)
        ax.set_xlim(0.0, 1.02)
        ax.set_yticks(range(len(labels)))
        ax.set_yticklabels(labels)
        ax.set_xlabel("Mapping confidence (0-1)")
        ax.set_title("Step 01 - HTSSF confidence by decomposed criterion", fontweight="bold")
        ax.axvline(0.80, color=C_AMBER, linestyle="--", linewidth=1.0, label="0.80 reference")
        for idx, (bar, value) in enumerate(zip(bars, values)):
            ax.text(min(value + 0.015, 1.0), idx, f"{value:.2f}", va="center", fontsize=8)
        ax.legend(fontsize=8)
        _save(fig, out_figs, "fig_01b_step01_confidence")

    score_cols = [col for col in ["top_fused_emb", "top_fused_bm25", "top_fused_tok", "top_fused_fuz"] if col in frame.columns]
    if score_cols:
        sub = frame[["variable_id", *score_cols]].copy().head(8)
        sub = sub.dropna(how="all", subset=score_cols)
        if not sub.empty:
            data = np.nan_to_num(sub[score_cols].apply(lambda column: column.map(_safe_float)).to_numpy())
            labels = sub["variable_id"].astype(str).tolist()
            component_labels = ["Dense", "BM25", "Token", "Fuzzy"][: len(score_cols)]
            colors = [C_BLUE, C_TEAL, C_GREEN, C_AMBER][: len(score_cols)]
            x = np.arange(len(labels))
            bottom = np.zeros(len(labels))
            fig, ax = plt.subplots(figsize=(8.8, 4.6))
            for idx, label in enumerate(component_labels):
                values = data[:, idx]
                ax.bar(x, values, bottom=bottom, color=colors[idx], alpha=0.85, label=label)
                bottom += values
            ax.set_xticks(x)
            ax.set_xticklabels(labels)
            ax.set_ylabel("HTSSF contribution")
            ax.set_title("Step 01 - Retrieval-score decomposition per criterion", fontweight="bold")
            ax.legend(fontsize=8, loc="upper right")
            _save(fig, out_figs, "fig_01c_step01_score_decomposition")


def fig_step02(run_root: Path, profile_id: str, out_figs: Path, out_tables: Path) -> None:
    print("\n[Step 02] Initial observation model")
    model = _load_step02_model(run_root, profile_id)
    if not model:
        print("  [warn] Step-02 model JSON missing.")
        return

    criteria = model.get("criteria_variables", []) or []
    predictors = model.get("predictor_variables", []) or []
    edges = model.get("edges", []) or []
    if not criteria or not predictors:
        print("  [warn] Step-02 model missing criteria/predictors.")
        return

    criterion_ids = [str(item.get("var_id") or item.get("variable_id") or f"C{idx + 1:02d}") for idx, item in enumerate(criteria)]
    predictor_ids = [str(item.get("var_id") or item.get("variable_id") or f"P{idx + 1:02d}") for idx, item in enumerate(predictors)]
    criterion_labels = [str(item.get("label") or item.get("variable_label") or criterion_ids[idx]) for idx, item in enumerate(criteria)]
    predictor_labels = [str(item.get("label") or item.get("variable_label") or predictor_ids[idx]) for idx, item in enumerate(predictors)]

    edge_map: Dict[tuple[str, str], float] = {}
    for edge in edges:
        predictor = str(
            edge.get("from_predictor_var_id")
            or edge.get("predictor_var_id")
            or edge.get("predictor_id")
            or ""
        ).strip()
        criterion = str(
            edge.get("to_criterion_var_id")
            or edge.get("criterion_var_id")
            or edge.get("criterion_id")
            or ""
        ).strip()
        relevance = _safe_float(
            edge.get("estimated_relevance_0_1")
            or edge.get("relevance_score_0_1")
            or edge.get("relevance_score_0_1_comma5")
        )
        if predictor and criterion:
            edge_map[(predictor, criterion)] = relevance

    overview = pd.DataFrame(
        {
            "Criterion ID": criterion_ids,
            "Criterion": [_shorten(label, 48) for label in criterion_labels],
            "Path": [_shorten_path(item.get("criterion_path"), keep=3, limit=62) for item in criteria],
        }
    )
    _write_csv(overview, out_tables, "table_02_step02_criteria")

    fig, ax = plt.subplots(figsize=(10.5, max(5.6, 0.75 * max(len(criterion_ids), len(predictor_ids)) + 1.0)))
    ax.set_xlim(-0.2, 3.3)
    cy = np.linspace(1, max(1, len(criterion_ids)), len(criterion_ids))[::-1]
    py = np.linspace(1, max(1, len(predictor_ids)), len(predictor_ids))[::-1]
    for (predictor, criterion), relevance in edge_map.items():
        if predictor not in predictor_ids or criterion not in criterion_ids:
            continue
        x0, y0 = 0.9, py[predictor_ids.index(predictor)]
        x1, y1 = 2.4, cy[criterion_ids.index(criterion)]
        ax.plot([x0, x1], [y0, y1], color=C_TEAL, alpha=0.18 + 0.72 * relevance, linewidth=0.5 + 2.8 * relevance)
    for idx, (criterion_id, label, y_pos) in enumerate(zip(criterion_ids, criterion_labels, cy)):
        ax.scatter([2.4], [y_pos], s=260, color=C_BLUE, edgecolors="white", linewidths=1.4, zorder=3)
        ax.text(2.56, y_pos, f"{criterion_id}: {_shorten(label, 34)}", va="center", fontsize=8)
    for idx, (predictor_id, label, y_pos) in enumerate(zip(predictor_ids, predictor_labels, py)):
        ax.scatter([0.9], [y_pos], s=210, marker="D", color=C_TEAL, edgecolors="white", linewidths=1.4, zorder=3)
        ax.text(0.76, y_pos, f"{predictor_id}: {_shorten(label, 34)}", va="center", ha="right", fontsize=8)
    ax.text(0.9, max(py.max() if len(py) else 1.0, 1.0) + 0.55, "Predictors", ha="center", fontsize=10, fontweight="bold", color=C_TEAL)
    ax.text(2.4, max(cy.max() if len(cy) else 1.0, 1.0) + 0.55, "Criteria", ha="center", fontsize=10, fontweight="bold", color=C_BLUE)
    ax.set_title("Step 02 - Initial criterion-predictor bipartite model", fontweight="bold")
    ax.axis("off")
    _save(fig, out_figs, "fig_02a_step02_bipartite_model")

    matrix = np.zeros((len(predictor_ids), len(criterion_ids)))
    for (predictor, criterion), relevance in edge_map.items():
        if predictor not in predictor_ids or criterion not in criterion_ids:
            continue
        matrix[predictor_ids.index(predictor), criterion_ids.index(criterion)] = relevance
    fig, ax = plt.subplots(
        figsize=(max(6.6, 1.2 * len(criterion_ids) + 2.0), max(4.2, 0.72 * len(predictor_ids) + 1.6))
    )
    image = ax.imshow(matrix, cmap="Blues", vmin=0.0, vmax=max(1e-6, float(matrix.max()) or 1.0), aspect="auto")
    ax.set_xticks(range(len(criterion_ids)))
    ax.set_xticklabels([f"{cid}\n{_shorten(label, 22)}" for cid, label in zip(criterion_ids, criterion_labels)], rotation=20, ha="right")
    ax.set_yticks(range(len(predictor_ids)))
    ax.set_yticklabels([f"{pid}: {_shorten(label, 28)}" for pid, label in zip(predictor_ids, predictor_labels)])
    for row in range(matrix.shape[0]):
        for col in range(matrix.shape[1]):
            if matrix[row, col] <= 0:
                continue
            ax.text(col, row, f"{matrix[row, col]:.2f}", ha="center", va="center", fontsize=7, color="white" if matrix[row, col] >= 0.45 else "black")
    plt.colorbar(image, ax=ax, label="Estimated relevance")
    ax.set_title("Step 02 - Predictor-to-criterion relevance heatmap", fontweight="bold")
    _save(fig, out_figs, "fig_02b_step02_relevance_heatmap")


def fig_pseudodata(run_root: Path, profile_id: str, out_figs: Path) -> None:
    print("\n[Pseudodata]")
    pseudo_dir = run_root / "02_pseudodata_generation" / "outputs" / "pseudodata" / profile_id
    frame = _load_csv(pseudo_dir / "pseudodata_wide.csv")
    if frame.empty:
        print("  [warn] pseudodata_wide.csv missing.")
        return
    time_col = next((col for col in frame.columns if "date" in col.lower() or "time" in col.lower()), frame.columns[0])
    numeric_cols = [col for col in frame.columns if col != time_col and pd.api.types.is_numeric_dtype(frame[col])]
    if not numeric_cols:
        print("  [warn] no numeric pseudodata columns.")
        return
    top_cols = frame[numeric_cols].var().sort_values(ascending=False).head(min(6, len(numeric_cols))).index.tolist()
    if not top_cols:
        return

    try:
        x_values = pd.to_datetime(frame[time_col])
    except Exception:
        x_values = np.arange(len(frame))

    fig, axes = plt.subplots(len(top_cols), 1, figsize=(12, max(4.0, 1.8 * len(top_cols))), sharex=True)
    if len(top_cols) == 1:
        axes = [axes]
    palette = [C_BLUE, C_TEAL, C_GREEN, C_AMBER, C_PURPLE, C_GREY]
    for idx, (column, axis) in enumerate(zip(top_cols, axes)):
        series = pd.to_numeric(frame[column], errors="coerce")
        color = palette[idx % len(palette)]
        axis.plot(x_values, series, color=color, linewidth=1.2)
        axis.fill_between(x_values, series, np.nanmin(series), alpha=0.08, color=color)
        axis.set_ylabel(column, color=color, fontweight="bold")
        axis.set_title(f"{column} ({'criterion' if column.startswith('C') else 'predictor'})", loc="left", fontsize=8.5)
    axes[-1].set_xlabel("Observation time")
    fig.suptitle(
        f"EMA pseudodata generated from the Step-02 model ({len(frame)} observations)",
        fontsize=10,
        fontweight="bold",
        y=1.01,
    )
    fig.tight_layout()
    _save(fig, out_figs, "fig_03_pseudodata_timeseries")


def fig_readiness(run_root: Path, profile_id: str, out_figs: Path) -> None:
    print("\n[Readiness]")
    payload = _load_json(run_root / "03_readiness_check" / profile_id / "readiness_report.json")
    overall = payload.get("overall", {}) if payload else {}
    if not overall:
        print("  [warn] readiness_report.json missing.")
        return

    readiness_score = _safe_float(overall.get("readiness_score_0_100"))
    readiness_label = str(overall.get("readiness_label") or overall.get("readiness_label_score_based") or "unknown")
    recommended_tier = str(overall.get("recommended_tier") or "unknown")
    tier_variant = str(overall.get("tier3_variant") or "")
    execution_plan = overall.get("analysis_execution_plan", {}) or {}
    ready_variables = overall.get("ready_variables", []) or []
    dropped_variables = overall.get("dropped_variables", []) or []
    if isinstance(ready_variables, dict):
        ready_variables = list(ready_variables.keys())
    elif not isinstance(ready_variables, list):
        ready_variables = [str(ready_variables)]
    if isinstance(dropped_variables, dict):
        dropped_variables = [f"{key}: {value}" for key, value in dropped_variables.items()]
    elif not isinstance(dropped_variables, list):
        dropped_variables = [str(dropped_variables)]

    fig = plt.figure(figsize=(11.5, 5.4))
    grid = gridspec.GridSpec(1, 3, width_ratios=[1.2, 1.4, 1.8], wspace=0.35)

    gauge_ax = fig.add_subplot(grid[0])
    theta = np.linspace(0, np.pi, 240)
    gauge_ax.plot(np.cos(theta), np.sin(theta), color=C_BORDER, linewidth=2.0)
    fraction = np.clip(readiness_score / 100.0, 0.0, 1.0)
    theta_score = np.linspace(0, np.pi * fraction, 240)
    score_color = C_GREEN if readiness_score >= 80 else C_AMBER if readiness_score >= 55 else C_RED
    gauge_ax.plot(np.cos(theta_score), np.sin(theta_score), color=score_color, linewidth=6.0)
    gauge_ax.scatter([np.cos(np.pi * fraction)], [np.sin(np.pi * fraction)], s=90, color=score_color, zorder=4)
    gauge_ax.text(0.0, -0.20, f"{readiness_score:.0f}/100", ha="center", fontsize=20, fontweight="bold", color=score_color)
    gauge_ax.text(0.0, -0.50, readiness_label.replace("_", " "), ha="center", fontsize=9, color=C_GREY)
    gauge_ax.text(0.0, 0.55, "Readiness score", ha="center", fontsize=9, fontweight="bold")
    gauge_ax.set_xlim(-1.3, 1.3)
    gauge_ax.set_ylim(-0.8, 1.15)
    gauge_ax.axis("off")

    info_ax = fig.add_subplot(grid[1])
    info_ax.axis("off")
    info_rows = [
        ("Recommended tier", recommended_tier),
        ("Tier variant", tier_variant or "n/a"),
        ("Execution set", str(execution_plan.get("analysis_set") or "n/a")),
        ("Lag", str((payload.get("meta", {}) or {}).get("lag_used") or "n/a")),
    ]
    for idx, (label, value) in enumerate(info_rows):
        y = 0.90 - idx * 0.18
        info_ax.text(0.0, y, f"{label}:", transform=info_ax.transAxes, fontsize=9, fontweight="bold", color=C_GREY)
        info_ax.text(0.52, y, value, transform=info_ax.transAxes, fontsize=9, color=C_BLUE)
    info_ax.set_title("HUA readiness classifier", fontsize=10, fontweight="bold")

    status_ax = fig.add_subplot(grid[2])
    status_ax.axis("off")
    status_ax.text(0.0, 0.94, "Variable gating", transform=status_ax.transAxes, fontsize=9, fontweight="bold", color=C_GREY)
    y = 0.84
    for variable in ready_variables[:8]:
        status_ax.text(0.0, y, f"OK  {variable}", transform=status_ax.transAxes, fontsize=8.4, color=C_GREEN)
        y -= 0.08
    if dropped_variables:
        y -= 0.03
        status_ax.text(0.0, y, "Dropped variables", transform=status_ax.transAxes, fontsize=9, fontweight="bold", color=C_GREY)
        y -= 0.08
        for variable in dropped_variables[:4]:
            status_ax.text(0.0, y, f"- {variable}", transform=status_ax.transAxes, fontsize=8.2, color=C_RED)
            y -= 0.08
    fig.suptitle("Step 03 - HUA readiness and method gating", fontsize=10, fontweight="bold")
    _save(fig, out_figs, "fig_04_readiness_dashboard")


def fig_network(run_root: Path, profile_id: str, out_figs: Path, out_tables: Path) -> None:
    print("\n[Network]")
    network_dir = run_root / "04_time_series_analysis" / "network" / profile_id
    comparison = _load_json(network_dir / "comparison_summary.json")
    metrics_dir = network_dir / "network_metrics"
    if not comparison or not metrics_dir.exists():
        print("  [warn] network outputs missing.")
        return

    global_metrics = _load_json(metrics_dir / "stationary_lagged_global_metrics.json")
    if not global_metrics:
        global_metrics = _load_json(metrics_dir / "stationary_contemp_global_metrics.json")

    node_centrality = _load_csv(metrics_dir / "stationary_lagged_node_centrality.csv")
    if node_centrality.empty:
        node_centrality = _load_csv(metrics_dir / "stationary_contemp_node_centrality.csv")
    if node_centrality.empty:
        node_centrality = _load_csv(metrics_dir / "temporal_lagged_node_centrality.csv")
    if node_centrality.empty:
        node_centrality = _load_csv(metrics_dir / "temporal_contemp_node_centrality.csv")
    if node_centrality.empty:
        node_centrality = _load_csv(metrics_dir / "predictor_importance_tv.csv")
        if not node_centrality.empty and "predictor" in node_centrality.columns:
            node_centrality = node_centrality.rename(
                columns={
                    "predictor": "node",
                    "out_strength_criteria_mean": "out_strength_abs",
                    "nonzero_fraction_mean": "pagerank",
                }
            )
    if not node_centrality.empty and "out_strength_abs" in node_centrality.columns:
        node_centrality = node_centrality.sort_values("out_strength_abs", ascending=False).head(10).copy()
        node_centrality["node_type"] = node_centrality["node"].astype(str).map(lambda value: "criterion" if value.startswith("C") else "predictor")
        _write_csv(node_centrality[["node", "out_strength_abs", "pagerank", "node_type"]], out_tables, "table_03_network_node_centrality")

    # If centrality files are absent/empty, construct a fallback centrality summary from observed data.
    if node_centrality.empty or "out_strength_abs" not in node_centrality.columns:
        z_path_fallback = network_dir / "data" / "X_imputed_zscored.csv"
        zf = _load_csv(z_path_fallback)
        if not zf.empty:
            usable_cols = [col for col in zf.columns if pd.api.types.is_numeric_dtype(zf[col])]
            if len(usable_cols) >= 4:
                corr = zf[usable_cols].corr().fillna(0.0)
                strength = corr.abs().sum(axis=1) - 1.0
                density_proxy = (corr.abs() > 0.25).sum(axis=1) - 1
                fallback = pd.DataFrame({
                    "node": strength.index.astype(str),
                    "out_strength_abs": strength.to_numpy(),
                    "pagerank": (density_proxy / max(1, len(corr.columns) - 1)).to_numpy(),
                })
                fallback["node_type"] = fallback["node"].map(lambda value: "criterion" if str(value).startswith("C") else "predictor")
                node_centrality = fallback.sort_values("out_strength_abs", ascending=False).head(10).copy()
                _write_csv(node_centrality[["node", "out_strength_abs", "pagerank", "node_type"]], out_tables, "table_03_network_node_centrality")

    fig, axes = plt.subplots(1, 2, figsize=(13.0, 5.4))
    if global_metrics:
        metric_keys = ["density", "transitivity", "avg_clustering", "global_efficiency_weighted", "modularity"]
        metric_labels = ["Density", "Transitivity", "Avg clustering", "Global efficiency", "Modularity"]
        metric_values = [_safe_float(global_metrics.get(key)) for key in metric_keys]
        bars = axes[0].bar(metric_labels, metric_values, color=[C_BLUE, C_TEAL, C_GREEN, C_AMBER, C_PURPLE], alpha=0.85)
        axes[0].set_ylim(0.0, max(metric_values + [0.1]) * 1.25)
        axes[0].tick_params(axis="x", rotation=18)
        axes[0].set_ylabel("Value")
        axes[0].set_title("Global network metrics", fontweight="bold")
        for bar, value in zip(bars, metric_values):
            axes[0].text(bar.get_x() + bar.get_width() / 2.0, bar.get_height() + 0.01, f"{value:.3f}", ha="center", va="bottom", fontsize=8)
    else:
        axes[0].text(0.5, 0.5, "No global metrics found", ha="center", va="center", transform=axes[0].transAxes)
        axes[0].set_title("Global network metrics", fontweight="bold")

    if not node_centrality.empty:
        colors = [C_BLUE if value == "criterion" else C_TEAL for value in node_centrality["node_type"].tolist()]
        axes[1].barh(node_centrality["node"].astype(str), node_centrality["out_strength_abs"], color=colors, alpha=0.85)
        axes[1].set_xlabel("Absolute out-strength")
        axes[1].set_title("Top node centrality values", fontweight="bold")
    else:
        axes[1].text(0.5, 0.5, "No node centrality file found", ha="center", va="center", transform=axes[1].transAxes)
        axes[1].set_title("Top node centrality values", fontweight="bold")

    execution_plan = comparison.get("execution_plan", {}) or {}
    fig.suptitle(
        f"Step 04 - Network time-series analysis ({execution_plan.get('analysis_set') or 'analysis_set_n/a'})",
        fontsize=10,
        fontweight="bold",
    )
    fig.tight_layout()
    _save(fig, out_figs, "fig_05_network_analysis")

    # Fallback dynamic network diagnostics from rolling correlations of observed series.
    z_path = network_dir / "data" / "X_imputed_zscored.csv"
    z_frame = _load_csv(z_path)
    if not z_frame.empty:
        usable_cols = [col for col in z_frame.columns if pd.api.types.is_numeric_dtype(z_frame[col])]
        if len(usable_cols) >= 4:
            data = z_frame[usable_cols].copy()
            n = len(data)
            win = max(24, n // 3)
            slices = [
                ("Early", 0, min(win, n)),
                ("Middle", max(0, n // 2 - win // 2), min(n, n // 2 + win // 2)),
                ("Late", max(0, n - win), n),
            ]
            fig, axes = plt.subplots(1, 3, figsize=(15.5, 4.8))
            for idx, (label, lo, hi) in enumerate(slices):
                segment = data.iloc[lo:hi, :]
                corr = segment.corr().fillna(0.0)
                top_vars = segment.var().sort_values(ascending=False).head(min(8, len(corr.columns))).index.tolist()
                corr = corr.loc[top_vars, top_vars]
                ax = axes[idx]
                ax.set_title(f"{label} window ({len(segment)} obs)", fontweight="bold", fontsize=9)
                theta = np.linspace(0, 2 * np.pi, len(top_vars), endpoint=False)
                positions = {
                    top_vars[i]: (np.cos(theta[i]), np.sin(theta[i])) for i in range(len(top_vars))
                }
                node_strength = corr.abs().mean(axis=1).to_dict()
                # Draw edges above a conservative threshold so the graph remains interpretable.
                for i, src in enumerate(top_vars):
                    for j, dst in enumerate(top_vars):
                        if j <= i:
                            continue
                        weight = float(corr.loc[src, dst])
                        if abs(weight) < 0.25:
                            continue
                        x0, y0 = positions[src]
                        x1, y1 = positions[dst]
                        edge_color = "#DC2626" if weight > 0 else "#2563EB"
                        ax.plot([x0, x1], [y0, y1], color=edge_color, alpha=min(0.85, 0.2 + abs(weight)), linewidth=0.8 + 2.0 * abs(weight), zorder=1)
                for var in top_vars:
                    x, y = positions[var]
                    size = 240 + 900 * float(node_strength.get(var, 0.0))
                    ax.scatter([x], [y], s=size, color="#0E7490", edgecolors="white", linewidths=1.0, zorder=2)
                    ax.text(x, y, _shorten(var, 12), ha="center", va="center", fontsize=7, color="white", zorder=3)
                ax.set_xlim(-1.35, 1.35)
                ax.set_ylim(-1.35, 1.35)
                ax.axis("off")
            fig.text(0.18, 0.04, "Red edge: positive relation", fontsize=8, color="#DC2626")
            fig.text(0.42, 0.04, "Blue edge: negative relation", fontsize=8, color="#2563EB")
            fig.text(0.66, 0.04, "Node size: mean absolute connectivity", fontsize=8, color="#0E7490")
            fig.suptitle("Step 04 - Time-varying network snapshots (early/mid/late windows)", fontsize=10, fontweight="bold")
            _save(fig, out_figs, "fig_05b_network_time_slices")


def fig_impact(run_root: Path, profile_id: str, out_figs: Path, out_tables: Path) -> None:
    print("\n[Impact]")
    impact_dir = run_root / "05_momentary_impact_coefficients" / profile_id
    composite = _load_csv(impact_dir / "predictor_composite.csv")
    impact_matrix = _load_csv(impact_dir / "impact_matrix.csv")
    if composite.empty and impact_matrix.empty:
        print("  [warn] impact outputs missing.")
        return

    if not composite.empty:
        composite = composite.sort_values("predictor_impact", ascending=False).head(12).copy()
        impact_table = composite[["predictor", "predictor_label", "predictor_impact", "predictor_rank"]].copy()
        impact_table["predictor_label"] = impact_table["predictor_label"].map(lambda value: _shorten(value, 46))
        impact_table["predictor_impact"] = impact_table["predictor_impact"].map(lambda value: round(_safe_float(value), 4))
        _write_csv(impact_table, out_tables, "table_04_predictor_impact_ranking")

        fig, ax = plt.subplots(figsize=(9.6, max(4.0, 0.56 * len(composite) + 1.0)))
        colors = [C_BLUE if idx < 3 else C_TEAL if idx < 6 else C_GREY for idx in range(len(composite))]
        labels = [f"{row.predictor}: {_shorten(row.predictor_label, 30)}" for row in composite.itertuples(index=False)]
        values = composite["predictor_impact"].map(_safe_float).tolist()
        bars = ax.barh(range(len(composite)), values, color=colors, alpha=0.86, height=0.64)
        ax.set_yticks(range(len(composite)))
        ax.set_yticklabels(labels)
        ax.set_xlabel("Composite predictor impact")
        ax.set_title("Step 05 - Momentary impact ranking", fontweight="bold")
        for idx, (bar, value) in enumerate(zip(bars, values)):
            ax.text(value + 0.01, idx, f"{value:.3f}", va="center", fontsize=8)
        _save(fig, out_figs, "fig_06a_impact_ranking")

    if not impact_matrix.empty:
        matrix = impact_matrix.copy()
        if "criterion" in matrix.columns:
            matrix = matrix.set_index("criterion")
        numeric = matrix.applymap(_safe_float)
        fig, ax = plt.subplots(figsize=(max(6.2, 1.1 * len(numeric.columns) + 1.6), max(4.0, 0.75 * len(numeric.index) + 1.2)))
        image = ax.imshow(numeric.to_numpy(), cmap="RdYlGn_r", vmin=0.0, vmax=max(1e-6, float(numeric.to_numpy().max()) or 1.0), aspect="auto")
        ax.set_xticks(range(len(numeric.columns)))
        ax.set_xticklabels(numeric.columns.tolist(), rotation=25, ha="right")
        ax.set_yticks(range(len(numeric.index)))
        ax.set_yticklabels(numeric.index.tolist())
        for row in range(numeric.shape[0]):
            for col in range(numeric.shape[1]):
                value = float(numeric.iloc[row, col])
                ax.text(col, row, f"{value:.2f}", ha="center", va="center", fontsize=7, color="white" if value >= 0.45 else "black")
        plt.colorbar(image, ax=ax, label="Impact coefficient")
        ax.set_title("Step 05 - Predictor-to-criterion impact matrix", fontweight="bold")
        _save(fig, out_figs, "fig_06b_impact_heatmap")


def fig_step03(run_root: Path, profile_id: str, out_figs: Path, out_tables: Path) -> None:
    print("\n[Step 03]")
    handoff_dir = run_root / "06_target_identification_and_model_update" / profile_id
    candidates = _load_csv(handoff_dir / "top_treatment_target_candidates.csv")
    selection = _load_json(handoff_dir / "step03_target_selection.json")
    if candidates.empty and not selection:
        print("  [warn] Step-03 outputs missing.")
        return

    if not candidates.empty:
        candidates = candidates.sort_values("selection_score_0_1", ascending=False).head(12).copy()
        candidate_table = candidates[
            ["predictor_rank", "predictor", "predictor_label", "selection_score_0_1", "mapped_leaf_path", "selected_for_intervention"]
        ].copy()
        candidate_table["predictor_label"] = candidate_table["predictor_label"].map(lambda value: _shorten(value, 42))
        candidate_table["mapped_leaf_path"] = candidate_table["mapped_leaf_path"].map(_shorten_path)
        _write_csv(candidate_table, out_tables, "table_05_step03_target_candidates")

        fig, ax = plt.subplots(figsize=(10.8, max(4.5, 0.56 * len(candidates) + 1.0)))
        labels = [f"{row.predictor}: {_shorten(row.predictor_label, 32)}" for row in candidates.itertuples(index=False)]
        values = candidates["selection_score_0_1"].map(_safe_float).tolist()
        colors = [C_GREEN if bool(flag) else C_GREY for flag in candidates["selected_for_intervention"].tolist()]
        ax.barh(range(len(candidates)), values, color=colors, alpha=0.88, height=0.64)
        ax.set_yticks(range(len(candidates)))
        ax.set_yticklabels(labels)
        ax.set_xlabel("Selection score")
        ax.set_title("Step 06 / Agentic Step 03 - Target-candidate ranking", fontweight="bold")
        _save(fig, out_figs, "fig_07a_step03_target_candidates")

    recommended_targets = selection.get("recommended_targets", []) if selection else []
    if recommended_targets:
        recommended_frame = pd.DataFrame(
            [
                {
                    "Predictor": item.get("predictor", ""),
                    "Label": _shorten(item.get("predictor_label", ""), 40),
                    "Score": round(_safe_float(item.get("score_0_1")), 3),
                    "Confidence": round(_safe_float(item.get("confidence_0_1")), 2),
                    "Mapped leaf": _shorten_path(item.get("mapped_leaf_path"), limit=60),
                }
                for item in recommended_targets
            ]
        )
        _write_csv(recommended_frame, out_tables, "table_06_step03_recommended_targets")
        _table_figure(
            recommended_frame,
            title="Step 03 - Recommended treatment targets",
            header_color=C_GREEN,
            zebra_color="#F0FDF4",
            out_dir=out_figs,
            name="fig_07b_step03_recommended_targets",
        )


def fig_step04(run_root: Path, profile_id: str, out_figs: Path, out_tables: Path) -> None:
    print("\n[Step 04]")
    handoff_dir = run_root / "06_target_identification_and_model_update" / profile_id
    updated_model = _load_json(handoff_dir / "step04_updated_observation_model.json")
    fusion = _load_json(handoff_dir / "step04_nomothetic_idiographic_fusion.json")
    fusion_rankings = _load_csv(handoff_dir / "step04_fusion_predictor_rankings.csv")
    fusion_matrix = _load_csv(handoff_dir / "step04_fusion_matrix.csv")
    if not updated_model and fusion_rankings.empty and fusion_matrix.empty:
        print("  [warn] Step-04 outputs missing.")
        return

    weights = fusion.get("weights", {}) if fusion else {}
    shortlist = updated_model.get("refined_predictor_shortlist", []) if updated_model else []
    if shortlist:
        shortlist_frame = pd.DataFrame(shortlist[:12])
        if not shortlist_frame.empty:
            shortlist_frame = shortlist_frame.rename(columns={"predictor_path": "Predictor path", "score_0_1": "Fusion score", "source": "Source", "reason": "Reason"})
            shortlist_frame["Predictor path"] = shortlist_frame["Predictor path"].map(lambda value: _shorten_path(value, keep=4, limit=68))
            shortlist_frame["Reason"] = shortlist_frame["Reason"].map(lambda value: _shorten(value, 54))
            _write_csv(shortlist_frame, out_tables, "table_07_step04_shortlist")

    if not fusion_matrix.empty:
        matrix = fusion_matrix.copy()
        if matrix.columns[0].startswith("Unnamed"):
            matrix = matrix.rename(columns={matrix.columns[0]: "criterion"}).set_index("criterion")
        numeric_all = matrix.applymap(_safe_float)
        col_spread = numeric_all.std(axis=0).sort_values(ascending=False)
        chosen_cols = col_spread.head(min(20, len(col_spread))).index.tolist()
        numeric = numeric_all.loc[:, chosen_cols]
        fig, ax = plt.subplots(figsize=(max(7.0, 1.0 * len(numeric.columns) + 1.8), max(4.0, 0.7 * len(numeric.index) + 1.3)))
        image = ax.imshow(numeric.to_numpy(), cmap="YlGnBu", vmin=0.0, vmax=max(1e-6, float(numeric.to_numpy().max()) or 1.0), aspect="auto")
        ax.set_xticks(range(len(numeric.columns)))
        ax.set_xticklabels([_shorten_path(column, keep=2, limit=28) for column in numeric.columns.tolist()], rotation=28, ha="right")
        ax.set_yticks(range(len(numeric.index)))
        ax.set_yticklabels(numeric.index.tolist())
        plt.colorbar(image, ax=ax, label="Fused score")
        ax.set_title("Step 07 / Agentic Step 04 - Fusion matrix (highest-variance predictors)", fontweight="bold")
        _save(fig, out_figs, "fig_08a_step04_fusion_matrix")

    if not fusion_rankings.empty:
        top_rankings = fusion_rankings.sort_values("fused_score_0_1", ascending=False).head(12).copy()
        fig, ax = plt.subplots(figsize=(11.8, max(4.5, 0.56 * len(top_rankings) + 1.0)))
        labels = top_rankings["predictor_path"].map(lambda value: _shorten_path(value, keep=3, limit=42)).tolist()
        values = top_rankings["fused_score_0_1"].map(_safe_float).tolist()
        nomo = top_rankings.get("nomothetic_mean_0_1", pd.Series([0.0] * len(top_rankings))).map(_safe_float).tolist()
        idio = top_rankings.get("idiographic_mean_0_1", pd.Series([0.0] * len(top_rankings))).map(_safe_float).tolist()
        y = np.arange(len(top_rankings))
        ax.barh(y + 0.22, values, color=C_PURPLE, alpha=0.86, height=0.20, label="Fused")
        ax.barh(y, nomo, color=C_BLUE, alpha=0.78, height=0.20, label="Nomothetic")
        ax.barh(y - 0.22, idio, color=C_TEAL, alpha=0.78, height=0.20, label="Idiographic")
        ax.set_yticks(range(len(top_rankings)))
        ax.set_yticklabels(labels)
        ax.set_xlabel("Score")
        ax.set_title("Step 07 / Agentic Step 04 - Refined predictor shortlist (score decomposition)", fontweight="bold")
        ax.legend(fontsize=8, loc="lower right")
        ax.text(
            0.99,
            0.02,
            f"nomothetic={_safe_float(weights.get('nomothetic_weight')):.2f} | idiographic={_safe_float(weights.get('idiographic_weight')):.2f}",
            transform=ax.transAxes,
            ha="right",
            fontsize=8,
            color=C_GREY,
        )
        _save(fig, out_figs, "fig_08b_step04_shortlist")

        # Variation diagnostic: show score spread directly.
        fig, ax = plt.subplots(figsize=(8.8, 3.8))
        spread = top_rankings[["fused_score_0_1", "nomothetic_mean_0_1", "idiographic_mean_0_1"]].copy()
        spread = spread.applymap(_safe_float)
        for col, color in [("fused_score_0_1", C_PURPLE), ("nomothetic_mean_0_1", C_BLUE), ("idiographic_mean_0_1", C_TEAL)]:
            ax.plot(np.arange(len(spread)), spread[col].to_numpy(), marker="o", linewidth=1.2, color=color, label=col.replace("_0_1", ""))
        all_vals = spread.to_numpy().reshape(-1)
        ymin = float(np.nanmin(all_vals))
        ymax = float(np.nanmax(all_vals))
        pad = max(0.002, (ymax - ymin) * 0.20)
        if np.isfinite(ymin) and np.isfinite(ymax):
            ax.set_ylim(max(0.0, ymin - pad), min(1.0, ymax + pad))
        ax.set_xticks(np.arange(len(spread)))
        ax.set_xticklabels([str(i + 1) for i in range(len(spread))])
        ax.set_xlabel("Rank position")
        ax.set_ylabel("Score")
        ax.set_title("Step 04 diagnostic - Top shortlist score spread (zoomed)", fontweight="bold")
        ax.legend(fontsize=8)
        _save(fig, out_figs, "fig_08c_step04_score_spread")

        # Delta diagnostic: make micro-variation explicit using milli-score units.
        fig, ax = plt.subplots(figsize=(8.8, 3.6))
        fused = np.array(values, dtype=float)
        if fused.size > 0:
            delta_ms = (fused[0] - fused) * 1000.0
            ax.bar(np.arange(len(delta_ms)), delta_ms, color=C_AMBER, alpha=0.85, width=0.72)
            ax.set_xticks(np.arange(len(delta_ms)))
            ax.set_xticklabels([str(i + 1) for i in range(len(delta_ms))])
            ax.set_xlabel("Rank position")
            ax.set_ylabel("Delta from top (milli-score)")
            ax.set_title("Step 04 diagnostic - Fused-score rank gaps", fontweight="bold")
            for i, dv in enumerate(delta_ms):
                ax.text(i, dv + max(0.02, 0.02 * (delta_ms.max() if len(delta_ms) else 1.0)), f"{dv:.2f}", ha="center", va="bottom", fontsize=7)
        _save(fig, out_figs, "fig_08d_step04_rank_gaps")


def fig_component_runtime_ms(run_roots: Sequence[Path], out_figs: Path, out_tables: Path) -> None:
    rows: List[Dict[str, Any]] = []
    seen: Dict[str, Dict[str, Any]] = {}
    for root in run_roots:
        if not root.exists():
            continue
        for trace_path in sorted(root.rglob("stage_trace.json")):
            payload = _load_json(trace_path)
            if not payload:
                continue
            stage = str(payload.get("stage") or trace_path.parent.name)
            status = str(payload.get("status") or "")
            rc = int(payload.get("return_code") or 0)
            if status not in {"completed", "skipped"}:
                continue
            if status == "completed" and rc != 0:
                continue
            key = stage
            record = {
                "Component": stage,
                "Status": status,
                "Runtime_ms": int(round(1000.0 * _safe_float(payload.get("duration_seconds")))),
                "Run": root.name,
            }
            seen[key] = record
    rows = [seen[key] for key in sorted(seen.keys())]
    if not rows:
        return
    frame = pd.DataFrame(rows).sort_values("Runtime_ms", ascending=False)
    _write_csv(frame, out_tables, "table_11_component_runtime_ms")

    fig, ax = plt.subplots(figsize=(10.8, max(4.0, 0.45 * len(frame) + 1.0)))
    y = np.arange(len(frame))
    colors = [C_GREEN if status == "completed" else C_GREY for status in frame["Status"].tolist()]
    bars = ax.barh(y, frame["Runtime_ms"].tolist(), color=colors, alpha=0.86)
    ax.set_yticks(y)
    ax.set_yticklabels(frame["Component"].tolist())
    ax.set_xlabel("Runtime (ms)")
    ax.set_title("PHOENIX component runtime breakdown", fontweight="bold")
    for bar, value in zip(bars, frame["Runtime_ms"].tolist()):
        ax.text(bar.get_width() + max(5, 0.01 * max(frame["Runtime_ms"].tolist())), bar.get_y() + bar.get_height() / 2, f"{int(value)}", va="center", fontsize=8)
    _save(fig, out_figs, "fig_11_component_runtime_ms")


def fig_step05(run_root: Path, profile_id: str, out_figs: Path, out_tables: Path) -> None:
    print("\n[Step 05]")
    intervention_dir = run_root / "07_hapa_digital_intervention" / profile_id
    payload = _load_json(intervention_dir / "step05_hapa_intervention.json")
    if not payload:
        print("  [warn] Step-05 outputs missing.")
        return

    barriers = payload.get("selected_barriers", []) or []
    coping = payload.get("selected_coping_strategies", []) or []
    hapa_plan = payload.get("hapa_component_plan", []) or []
    phased_plan = payload.get("phased_delivery_plan", []) or []
    generated_message = str(payload.get("singular_intervention_message") or payload.get("personalized_message") or "").strip()

    if barriers:
        barrier_frame = pd.DataFrame(
            [
                {
                    "Barrier": item.get("barrier_name", ""),
                    "HAPA path": _shorten_path(item.get("barrier_path"), keep=2, limit=56),
                    "Score": round(_safe_float(item.get("score_0_1")), 3),
                    "Rationale": _shorten(item.get("rationale", ""), 70),
                }
                for item in barriers[:10]
            ]
        )
        _write_csv(barrier_frame, out_tables, "table_08_step05_selected_barriers")
        fig, ax = plt.subplots(figsize=(9.6, max(4.0, 0.60 * len(barriers[:10]) + 1.0)))
        labels = [f"{_shorten(item.get('barrier_name', ''), 30)} | {_shorten_path(item.get('barrier_path'), keep=2, limit=22)}" for item in barriers[:10]]
        values = [_safe_float(item.get("score_0_1")) for item in barriers[:10]]
        bars = ax.barh(range(len(values)), values, color=plt.cm.RdYlGn_r(np.linspace(0.2, 0.85, len(values))), alpha=0.88, height=0.64)
        ax.set_yticks(range(len(values)))
        ax.set_yticklabels(labels)
        ax.set_xlabel("Barrier score")
        ax.set_title("Step 08 / Agentic Step 05 - Ranked HAPA barriers", fontweight="bold")
        for idx, (bar, value) in enumerate(zip(bars, values)):
            ax.text(value + 0.008, idx, f"{value:.3f}", va="center", fontsize=8)
        _save(fig, out_figs, "fig_09a_step05_barriers")

    if coping:
        coping_frame = pd.DataFrame(
            [
                {
                    "Strategy": _shorten(item.get("coping_name", ""), 34),
                    "Linked barriers": ", ".join([_shorten(barrier, 16) for barrier in item.get("linked_barriers", [])[:2]]),
                    "Score": round(_safe_float(item.get("score_0_1")), 3),
                    "Path": _shorten_path(item.get("coping_path"), keep=2, limit=46),
                }
                for item in coping[:10]
            ]
        )
        _write_csv(coping_frame, out_tables, "table_09_step05_coping_strategies")
        _table_figure(
            coping_frame,
            title="Step 05 - Selected coping strategies",
            header_color=C_PURPLE,
            zebra_color="#F5F3FF",
            out_dir=out_figs,
            name="fig_09b_step05_coping_strategies",
        )

    if hapa_plan:
        fig, ax = plt.subplots(figsize=(12.0, max(4.5, 1.0 * len(hapa_plan) + 1.0)))
        phase_colors = [C_BLUE, C_TEAL, C_GREEN, C_AMBER, C_PURPLE]
        ax.set_xlim(0.0, 1.0)
        ax.set_ylim(-0.5, len(hapa_plan) - 0.5)
        ax.axis("off")
        for idx, item in enumerate(hapa_plan):
            y_pos = len(hapa_plan) - idx - 1
            color = phase_colors[idx % len(phase_colors)]
            rect = mpatches.FancyBboxPatch((0.02, y_pos - 0.34), 0.96, 0.68, boxstyle="round,pad=0.02", facecolor=f"{color}20", edgecolor=color, linewidth=1.4)
            ax.add_patch(rect)
            ax.text(0.04, y_pos + 0.12, _shorten(item.get("component", ""), 54), fontsize=9, fontweight="bold", color=color)
            ax.text(0.04, y_pos - 0.02, f"Objective: {_shorten(item.get('objective', ''), 88)}", fontsize=8, color=C_GREY)
            ax.text(0.04, y_pos - 0.17, f"Digital delivery: {_shorten(item.get('digital_delivery', ''), 86)}", fontsize=8, color=C_GREY, style="italic")
        ax.set_title("Step 08 / Agentic Step 05 - HAPA component plan", fontsize=10, fontweight="bold")
        _save(fig, out_figs, "fig_09c_step05_hapa_plan")

    if phased_plan:
        fig, ax = plt.subplots(figsize=(11.0, max(3.6, 0.95 * len(phased_plan) + 1.2)))
        cmap = plt.get_cmap("Set2")
        for idx, item in enumerate(phased_plan):
            phase_name = str(item.get("phase") or f"Phase {idx + 1}")
            window = str(item.get("time_window") or "")
            start_day, end_day = idx * 7 + 1, idx * 7 + 7
            try:
                clean = window.lower().replace("days", "").replace("day", "").strip()
                left, right = [token.strip() for token in clean.split("-")]
                start_day, end_day = int(left), int(right)
            except Exception:
                pass
            ax.barh(idx, end_day - start_day + 1, left=start_day - 1, color=cmap(idx / max(1, len(phased_plan))), alpha=0.84, height=0.62)
            ax.text(start_day - 0.7, idx, f"{phase_name}: {_shorten(item.get('primary_goal', ''), 56)}", va="center", fontsize=8)
        ax.set_xlabel("Intervention day")
        ax.set_yticks(range(len(phased_plan)))
        ax.set_yticklabels([str(item.get("phase") or f"Phase {idx + 1}") for idx, item in enumerate(phased_plan)])
        ax.set_title("Step 08 / Agentic Step 05 - Phased EMA delivery plan", fontweight="bold")
        _save(fig, out_figs, "fig_09d_step05_phased_delivery")

    if generated_message:
        fig, ax = plt.subplots(figsize=(10.8, 3.2))
        ax.axis("off")
        wrapped = textwrap.fill(generated_message, width=110)
        ax.text(0.02, 0.72, "Generated mobile intervention message", fontsize=10, fontweight="bold", color=C_BLUE, transform=ax.transAxes)
        ax.text(0.02, 0.52, wrapped, fontsize=9, color=C_GREY, transform=ax.transAxes, va="top")
        ax.text(0.02, 0.08, "Source: step05_hapa_intervention.json -> singular_intervention_message", fontsize=7.8, color="#64748B", transform=ax.transAxes)
        _save(fig, out_figs, "fig_09e_step05_generated_message")


def fig_pipeline_summary(run_root: Path, profile_id: str, out_figs: Path, out_tables: Path) -> None:
    print("\n[Pipeline summary]")
    summary = _load_json(run_root / "pipeline_summary.json")
    if not summary:
        print("  [warn] pipeline_summary.json missing.")
        return
    stage_results = summary.get("stage_results", []) or []
    if not stage_results:
        print("  [warn] no stage results in pipeline summary.")
        return

    frame = pd.DataFrame(stage_results)
    if not frame.empty:
        export = frame[["stage", "return_code", "duration_seconds", "log_path"]].copy()
        _write_csv(export, out_tables, "table_10_pipeline_stage_results")

    labels = [str(item.get("stage", "")) for item in stage_results]
    durations = [_safe_float(item.get("duration_seconds")) for item in stage_results]
    return_codes = [int(item.get("return_code", 1)) for item in stage_results]
    colors = [C_GREEN if code == 0 else C_RED for code in return_codes]

    fig, axes = plt.subplots(1, 2, figsize=(13.0, 5.0))
    bars = axes[0].bar(range(len(labels)), durations, color=colors, alpha=0.86, width=0.72)
    axes[0].set_xticks(range(len(labels)))
    axes[0].set_xticklabels([label.replace("_", "\n") for label in labels], fontsize=7.5)
    axes[0].set_ylabel("Duration (seconds)")
    axes[0].set_title("Stage durations", fontweight="bold")
    for bar, value in zip(bars, durations):
        axes[0].text(bar.get_x() + bar.get_width() / 2.0, bar.get_height() + 0.4, f"{value:.0f}s", ha="center", va="bottom", fontsize=7.5)

    succeeded = sum(1 for code in return_codes if code == 0)
    failed = len(return_codes) - succeeded
    axes[1].pie(
        [max(succeeded, 0), max(failed, 0)],
        labels=["Succeeded", "Failed"],
        colors=[C_GREEN, C_RED],
        autopct="%1.0f%%",
        startangle=90,
        textprops={"fontsize": 10},
    )
    axes[1].set_title("Stage-status split", fontweight="bold")

    fig.suptitle(
        f"PHOENIX example run summary ({summary.get('run_id', run_root.name)} | {profile_id})",
        fontsize=10,
        fontweight="bold",
    )
    fig.tight_layout()
    _save(fig, out_figs, "fig_10_pipeline_summary")


def main() -> None:
    args = parse_args()
    run_root = Path(args.run_root).expanduser().resolve()
    profile_id = str(args.profile_id).strip()
    out_figs = Path(args.figures_dir).expanduser().resolve()
    out_tables = Path(args.tables_dir).expanduser().resolve()
    out_figs.mkdir(parents=True, exist_ok=True)
    out_tables.mkdir(parents=True, exist_ok=True)
    timing_roots = [run_root, *[Path(item).expanduser().resolve() for item in list(args.timing_root or [])]]

    print("=== PHOENIX example figures ===")
    print(f"Run root : {run_root}")
    print(f"Profile  : {profile_id}")
    print(f"Figures  : {out_figs}")
    print(f"Tables   : {out_tables}")

    if not run_root.exists():
        raise SystemExit(f"Run root does not exist: {run_root}")

    _copy_architecture_figure(out_figs)
    _copy_native_pipeline_visuals(run_root, out_figs)
    fig_step01(run_root, profile_id, out_figs, out_tables)
    fig_step02(run_root, profile_id, out_figs, out_tables)
    fig_pseudodata(run_root, profile_id, out_figs)
    fig_readiness(run_root, profile_id, out_figs)
    fig_network(run_root, profile_id, out_figs, out_tables)
    fig_impact(run_root, profile_id, out_figs, out_tables)
    fig_step03(run_root, profile_id, out_figs, out_tables)
    fig_step04(run_root, profile_id, out_figs, out_tables)
    fig_step05(run_root, profile_id, out_figs, out_tables)
    fig_pipeline_summary(run_root, profile_id, out_figs, out_tables)
    fig_component_runtime_ms(timing_roots, out_figs, out_tables)
    print("=== done ===")


if __name__ == "__main__":
    main()
