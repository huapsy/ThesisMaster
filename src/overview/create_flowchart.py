"""
create_flowchart.py
===================
Generates a research-grade, white-background architecture diagram for
the PHOENIX Engine, formalised as a Multi-Agent System.

Facts:
 - Input: free-text mental health complaint (NOT EMA data)
 - No orchestrator — pre-determined sequential stage sequence
 - EMA data collection happens AFTER the initial model is built
 - Steps 03 + 04 LLM calls are co-located in 01_prepare_targets_from_impact.py
 - Step 01: HTSSF (embedding + BM25 + fuzzy) + LLM adjudication → CRITERION leaf
 - BFS scoring: 0.45·mapping + 0.25·HyDE + 0.20·idiographic + 0.10·domain
 - Step 05: HAPA barrier/coping/phased-delivery plan

Run:
    python src/overview/create_flowchart.py
"""

from __future__ import annotations
from pathlib import Path
import matplotlib
matplotlib.use("Agg")
import matplotlib.patches as mpatches
import matplotlib.pyplot as plt
from matplotlib.patches import FancyArrowPatch, FancyBboxPatch
from matplotlib.lines import Line2D

# ---------------------------------------------------------------------------
# COLOUR PALETTE  (light / white background, publication-quality)
# ---------------------------------------------------------------------------
BG         = "#FFFFFF"
PANEL_BG   = "#F8FAFC"
BORDER_MID = "#CBD5E1"
TEXT_DARK  = "#0F172A"
TEXT_MID   = "#475569"
TEXT_LIGHT = "#94A3B8"

# Agent node fills and borders  (border is solid, fill is very light tint)
B_INPUT    = "#1D4ED8";  F_INPUT   = "#EFF6FF"
B_LLM      = "#0369A1";  F_LLM     = "#F0F9FF"
B_CRITIC   = "#B45309";  F_CRITIC  = "#FFFBEB"
B_HUA      = "#047857";  F_HUA     = "#ECFDF5"
B_DATA     = "#374151";  F_DATA    = "#F9FAFB"
B_MEMORY   = "#6D28D9";  F_MEMORY  = "#F5F3FF"
B_OUTPUT   = "#15803D";  F_OUTPUT  = "#F0FDF4"
B_ONTO     = "#64748B";  F_ONTO    = "#F8FAFC"
B_BFS      = "#0E7490";  F_BFS     = "#ECFEFF"

# Arrow colours
E_FWD      = "#0369A1"
E_CRITIC   = "#B45309"
E_CYCLE    = "#6D28D9"
E_HUA      = "#047857"
E_ONTO     = "#94A3B8"

ROUNDING   = 0.025
FIG_W      = 29.5
FIG_H      = 33
DPI        = 160

# ---------------------------------------------------------------------------
# HELPERS
# ---------------------------------------------------------------------------

def box(ax, cx, cy, w, h, title, sub=None,
        bc=B_LLM, fc=F_LLM, bold=False, fontsize=8.5,
        badge=None, badge_bc=None, badge_fc=None):
    x0, y0 = cx - w/2, cy - h/2
    patch = FancyBboxPatch((x0, y0), w, h,
                           boxstyle=f"round,pad={ROUNDING}",
                           linewidth=1.4, edgecolor=bc,
                           facecolor=fc, zorder=3)
    ax.add_patch(patch)
    ya = cy + (0.14 if sub else 0)
    ax.text(cx, ya, title, ha="center", va="center",
            fontsize=fontsize, fontweight="bold" if bold else "normal",
            color=TEXT_DARK, zorder=4, multialignment="center")
    if sub:
        ax.text(cx, cy - 0.19, sub,
                ha="center", va="center",
                fontsize=max(5.5, fontsize - 2.0), color=TEXT_MID,
                style="italic", zorder=4, multialignment="center")
    if badge and badge_bc:
        bw, bh = 0.58, 0.20
        bx0 = x0 + 0.07
        by0 = cy + h/2 - 0.25
        bp = FancyBboxPatch((bx0, by0), bw, bh,
                            boxstyle="round,pad=0.02",
                            linewidth=0, facecolor=badge_bc or bc, zorder=5)
        ax.add_patch(bp)
        ax.text(bx0 + bw/2, by0 + bh/2, badge,
                ha="center", va="center", fontsize=6.5,
                color="white", fontweight="bold", zorder=6)


def arr(ax, x0, y0, x1, y1, label="", color=E_FWD, lw=1.3, rad=0.0,
        tx=0.0, ty=0.0, ha="center", va="center"):
    a = FancyArrowPatch((x0, y0), (x1, y1),
                        arrowstyle="-|>",
                        connectionstyle=f"arc3,rad={rad}",
                        color=color, linewidth=lw,
                        zorder=2, mutation_scale=10)
    ax.add_patch(a)
    if label:
        import math
        mx, my = (x0+x1)/2, (y0+y1)/2
        if rad != 0:
            dx = x1 - x0
            dy = y1 - y0
            d = math.hypot(dx, dy)
            if d > 0:
                nx = -dy / d
                ny = dx / d
                mx += nx * (rad * d * 0.5)
                my += ny * (rad * d * 0.5)

        ax.text(mx + tx, my + ty, label, ha=ha, va=va,
                fontsize=5.8, color=color, zorder=5, style="italic",
                bbox=dict(boxstyle="round,pad=0.10",
                          facecolor="white", edgecolor="none", alpha=0.85))


def sect_label(ax, x, y, text):
    ax.text(x, y, text, ha="center", va="center",
            fontsize=7, fontweight="bold", color=TEXT_LIGHT,
            style="italic")


def bg_panel(ax, cx, cy, w, h, fc=PANEL_BG, bc=BORDER_MID, label=""):
    x0, y0 = cx - w/2, cy - h/2
    r = plt.Rectangle((x0, y0), w, h, facecolor=fc,
                       edgecolor=bc, linewidth=0.6,
                       linestyle=(0, (4, 3)), alpha=1.0, zorder=1)
    ax.add_patch(r)
    if label:
        ax.text(cx, cy + h/2 - 0.25, label,
                ha="center", va="top", fontsize=7.5,
                color=TEXT_MID, fontweight="bold", style="italic", zorder=2)


# ---------------------------------------------------------------------------
# DIAGRAM
# ---------------------------------------------------------------------------

def build():
    fig, ax = plt.subplots(figsize=(FIG_W, FIG_H), facecolor=BG)
    ax.set_facecolor(BG)
    ax.set_xlim(0, FIG_W)
    ax.set_ylim(0, FIG_H)
    ax.set_aspect("equal")
    ax.axis("off")

    # thin outer frame
    for spine_loc in ["top", "right", "bottom", "left"]:
        pass  # already off

    # ── Title ────────────────────────────────────────────────────────────────
    ax.text(FIG_W/2, 31.85,
            "PHOENIX engine — Multi Agent System Architecture",
            ha="center", fontsize=20, fontweight="bold", color=TEXT_DARK)

    # thin rule under title
    ax.axhline(31.4, xmin=0.02, xmax=0.98, color=BORDER_MID, lw=0.8)

    # ── Column X positions ───────────────────────────────────────────────────
    Cx  = 9.0     # main LLM spine
    Kx  = 19.0    # critics
    Hx  = 24.5    # HUA column

    # ── Row Y positions ──────────────────────────────────────────────────────
    y_complaint = 30.3
    y_s01       = 28.2
    y_s02       = 25.6
    y_s02c      = 25.6
    y_ema1      = 22.9
    y_rdy       = 22.9
    y_net       = 20.5
    y_imp       = 18.1
    y_bfs       = 16.1
    y_s03       = 14.0
    y_s03c      = 14.0
    y_s04       = 11.4
    y_s04c      = 11.4
    y_s05       =  8.7
    y_s05c      =  8.7
    y_arts      =  5.9
    y_hist      =  3.8
    y_ema2      =  1.7

    # ── Background panels ────────────────────────────────────────────────────
    bg_panel(ax, 16.35, 18.8, 23.3, 20.8,
             label="Multi-agent System")
    bg_panel(ax, Hx, 20.0, 6.8, 9.4,
             fc="#F0FDF4", bc="#86EFAC",
             label="Hierarchical Updating Algorithm (HUA)")



    # ── INPUT ────────────────────────────────────────────────────────────────
    box(ax, Cx, y_complaint, 10.0, 0.72,
        "Free-Text Mental Health Complaint",
        sub="complaint_text  ·  person_text  ·  context_text  (pseudoprofile input)",
        bc=B_INPUT, fc=F_INPUT, bold=True, badge="INPUT", badge_bc=B_INPUT)
    arr(ax, Cx, y_complaint-0.36, Cx, y_s01+0.44, color=E_FWD)

    # ── STEP 01 — Complaint Operationalization Agent ─────────────────────────
    box(ax, Cx, y_s01, 8.5, 0.80,
        "Complaint Operationalization Agent",
        sub=("Step 01  ·  HTSSF fusion: dense embedding (text-embedding-3-small)  +  BM25  +  token-overlap  +  fuzzy\n"
             "LLM adjudication (re-rank top-50)  →  single CRITERION ontology leaf node"),
        bc=B_LLM, fc=F_LLM, bold=True, badge="LLM-GEN", badge_bc=B_LLM)
    arr(ax, Cx, y_s01-0.40, Cx, y_s02+0.41,
        label="operationalized criterion leaf", color=E_FWD)

    # ── STEP 02a — Initial Observation Model Constructor ─────────────────────
    box(ax, Cx, y_s02, 8.5, 0.84,
        "Initial Observation Model Constructor Agent",
        sub=("Step 02a  ·  builds criterion × predictor bipartite network\n"
             "HyDE-based predictor RAG  ·  PREDICTOR ontology mapping  ·  relevance_score_0_1 per edge"),
        bc=B_LLM, fc=F_LLM, bold=True, badge="LLM-GEN", badge_bc=B_LLM)

    # ── STEP 02b — Critic ────────────────────────────────────────────────────
    box(ax, Kx, y_s02c, 8.5, 0.84,
        "Initial Model Critic Agent",
        sub=("Step 02b  ·  predictor_grounding · criterion_continuity\n"
             "· ontology_strictness · evidence_quality  →  PASS / REVISE  (max 2 revisions)"),
        bc=B_CRITIC, fc=F_CRITIC, bold=True, badge="CRITIC", badge_bc=B_CRITIC)

    arr(ax, Cx+4.25, y_s02, Kx-4.25, y_s02c, label="draft model", color=E_FWD)
    arr(ax, Kx-4.25, y_s02c-0.26, Cx+4.25, y_s02-0.26,
        label="REVISE", color=E_CRITIC, rad=0.0, lw=1.0)

    arr(ax, Cx, y_s02-0.42, Cx, y_ema1+0.38,
        label="PASS: initial model", color=E_FWD)

    # ── EMA DATA COLLECTION 1 ────────────────────────────────────────────────
    box(ax, Cx, y_ema1, 8.5, 0.72,
        "EMA Data Collection  (guided by initial model)",
        sub="EMA items determined by Step 02 predictor selection  ·  per-participant idiographic time-series",
        bc=B_DATA, fc=F_DATA, fontsize=8.2)
    arr(ax, Cx, y_ema1-0.36, Cx-0.5, y_rdy-0.01,
        label="EMA time-series", color=E_FWD)
    arr(ax, Cx+4.25, y_ema1, Hx-3.4, y_rdy,
        label="EMA series→HUA", color=E_HUA, lw=1.0)

    # ── HUA: READINESS CLASSIFIER ────────────────────────────────────────────
    box(ax, Hx, y_rdy, 6.5, 0.84,
        "Readiness Classifier",
        sub=("HUA — 01_check_readiness\n"
             "variance / stationarity / n-obs  →  readiness_report.json\n"
             "selects analytic tier: tv-gVAR / gVAR / baseline"),
        bc=B_HUA, fc=F_HUA, bold=True, badge="HUA", badge_bc=B_HUA)

    arr(ax, Hx, y_rdy-0.42, Hx, y_net+0.38,
        label="readiness plan", color=E_HUA)

    # ── HUA: NETWORK TIME-SERIES ANALYST ─────────────────────────────────────
    box(ax, Hx, y_net, 6.5, 0.80,
        "Network Time-Series Analyst",
        sub=("HUA — 01_time_series_analysis\n"
             "tv-gVAR  /  stationary gVAR  /  baseline\n"
             "→  contemporaneous & temporal edge weights"),
        bc=B_HUA, fc=F_HUA, bold=True, badge="HUA", badge_bc=B_HUA)

    arr(ax, Hx, y_net-0.40, Hx, y_imp+0.40,
        label="network edges", color=E_HUA)

    # ── HUA: MOMENTARY IMPACT QUANTIFIER ─────────────────────────────────────
    box(ax, Hx, y_imp, 6.5, 0.84,
        "Momentary Impact Quantifier",
        sub=("HUA — 02_hierarchical_update_ranking\n"
             "predictor-level impact coefficients\n"
             "→  impact_matrix.csv  (criterion × predictor)"),
        bc=B_HUA, fc=F_HUA, bold=True, badge="HUA", badge_bc=B_HUA)

    arr(ax, Hx, y_imp-0.42, Hx, y_bfs+0.48,
        label="impact_by_predictor\n+ ontology leaf paths", color=E_HUA)

    # impact → S04
    arr(ax, Hx-3.25, y_imp, Cx+4.25, y_s04+0.30,
        label="impact_matrix.csv\nreadiness_0_1", color=E_HUA, lw=1.0)

    # ── BFS CANDIDATE SELECTOR ───────────────────────────────────────────────
    box(ax, Hx, y_bfs, 6.5, 0.90,
        "BFS Candidate Selector",
        sub=("score = 0.45·mapping + 0.25·HyDE + 0.20·idiographic_anchor + 0.10·domain_bonus\n"
             "phases:  breadth_domain_coverage → breadth_round_robin → depth_refinement\n"
             "(target_refinement.py: build_bfs_candidates)"),
        bc=B_BFS, fc=F_BFS, bold=True, badge="BFS", badge_bc=B_BFS)

    arr(ax, Hx-3.25, y_bfs, Cx+4.25, y_s03,
        label="ranked candidate paths", color=E_FWD, lw=1.1)

    # ── STEP 03a — Treatment Target Identifier ────────────────────────────────
    box(ax, Cx, y_s03, 8.5, 0.90,
        "Treatment Target Identifier Agent",
        sub=("Step 03a  ·  01_prepare_targets_from_impact.py\n"
             "integrates: readiness · impact · network metrics · BFS candidates · initial model · profile text\n"
             "→  ranked_predictors  +  recommended_targets (≤ 3)"),
        bc=B_LLM, fc=F_LLM, bold=True, badge="LLM-GEN", badge_bc=B_LLM)

    # ── STEP 03b — Target Critic ──────────────────────────────────────────────
    box(ax, Kx, y_s03c, 8.5, 0.90,
        "Target Selection Critic Agent",
        sub=("Step 03b  ·  predictor_grounding · evidence_quality\n"
             "· data_limitations · ontology_strictness · safety_considerations\n"
             "→  PASS / REVISE  (max 2 revisions)"),
        bc=B_CRITIC, fc=F_CRITIC, bold=True, badge="CRITIC", badge_bc=B_CRITIC)

    arr(ax, Cx+4.25, y_s03, Kx-4.25, y_s03c, label="target selection", color=E_FWD)
    arr(ax, Kx-4.25, y_s03c-0.28, Cx+4.25, y_s03-0.28,
        label="REVISE", color=E_CRITIC, rad=0.0, lw=1.0)

    arr(ax, Cx, y_s03-0.45, Cx, y_s04+0.45,
        label="PASS: approved targets", color=E_FWD)

    # ── STEP 04a — Update Observation Model Actor ─────────────────────────────
    box(ax, Cx, y_s04, 8.5, 0.90,
        "Update Observation Model Actor",
        sub=("Step 04a  ·  fuse_updated_model_matrix (co-located in 01_prepare_targets_from_impact.py)\n"
             "nomothetic_weight = 1 − (0.30 + 0.50·readiness)  ·  idiographic_weight adaptive\n"
             "→  refined_predictor_shortlist  ·  recommended_next_observation_predictors"),
        bc=B_LLM, fc=F_LLM, bold=True, badge="LLM-GEN", badge_bc=B_LLM)

    # ── STEP 04b — Updated Model Critic ──────────────────────────────────────
    box(ax, Kx, y_s04c, 8.5, 0.90,
        "Updated Model Critic Agent",
        sub=("Step 04b  ·  predictor_grounding · criterion_continuity\n"
             "· bfs_depth_balance · fusion_consistency\n"
             "→  PASS / REVISE  (max 2 revisions)"),
        bc=B_CRITIC, fc=F_CRITIC, bold=True, badge="CRITIC", badge_bc=B_CRITIC)

    arr(ax, Cx+4.25, y_s04, Kx-4.25, y_s04c, label="updated model", color=E_FWD)
    arr(ax, Kx-4.25, y_s04c-0.28, Cx+4.25, y_s04-0.28,
        label="REVISE", color=E_CRITIC, rad=0.0, lw=1.0)

    arr(ax, Cx, y_s04-0.45, Cx, y_s05+0.45,
        label="PASS: updated obs. model", color=E_FWD)

    # ── STEP 05a — Generate HAPA-based Intervention Actor ────────────────────
    box(ax, Cx, y_s05, 8.5, 0.94,
        "Generate HAPA-based Intervention Actor",
        sub=("Step 05a  ·  01_generate_hapa_digital_intervention.py\n"
             "barrier = 0.60·predictor + 0.20·profile + 0.15·context + 0.05·complaint_match\n"
             "→  selected_targets · selected_barriers · coping_strategies · phased EMA delivery plan"),
        bc=B_LLM, fc=F_LLM, bold=True, badge="LLM-GEN", badge_bc=B_LLM)

    # ── STEP 05b — Intervention Critic ───────────────────────────────────────
    box(ax, Kx, y_s05c, 8.5, 0.94,
        "Intervention Critic Agent",
        sub=("Step 05b  ·  reasoning_quality·0.17 · evidence_grounding·0.21\n"
             "hapa_consistency·0.16 · medical_safety·0.16 · feasibility·0.10 · ethics·0.08\n"
             "→  PASS / REVISE  (max 2)  ·  ontology hard-enforcement on all paths"),
        bc=B_CRITIC, fc=F_CRITIC, bold=True, badge="CRITIC", badge_bc=B_CRITIC)

    arr(ax, Cx+4.25, y_s05, Kx-4.25, y_s05c, label="intervention plan", color=E_FWD)
    arr(ax, Kx-4.25, y_s05c-0.30, Cx+4.25, y_s05-0.30,
        label="REVISE", color=E_CRITIC, rad=0.0, lw=1.0)

    arr(ax, Cx, y_s05-0.47, Cx, y_arts+0.50,
        label="PASS: approved intervention", color=E_FWD)

    # ── RUN ARTIFACTS ─────────────────────────────────────────────────────────
    box(ax, Cx, y_arts, 8.5, 0.88,
        "Run Artifacts & Performance Report",
        sub=("step03_target_candidates.json  ·  step04_updated_observation_model.json\n"
             "step05_intervention_plan.json  ·  stage_trace.json  ·  stage_events.jsonl"),
        bc=B_OUTPUT, fc=F_OUTPUT, bold=True, badge="OUTPUT", badge_bc=B_OUTPUT)

    arr(ax, Cx, y_arts-0.44, Cx, y_hist+0.36,
        label="append cycle N artifacts", color=B_OUTPUT, lw=1.1)

    # ── HISTORY LEDGER ────────────────────────────────────────────────────────
    box(ax, Cx, y_hist, 8.5, 0.72,
        "History Ledger  ·  Iterative Memory",
        sub="profile_history.jsonl  ·  cycle_summary.json  ·  previous_cycle_scores  ·  stability_bonus_0_1",
        bc=B_MEMORY, fc=F_MEMORY, fontsize=8.2)

    arr(ax, Cx, y_hist-0.36, Cx, y_ema2+0.36,
        label="memory seed Cycle N+1", color=E_CYCLE)

    # ── EMA DATA COLLECTION 2 (updated model, next cycle) ────────────────────
    box(ax, Cx, y_ema2, 8.5, 0.72,
        "EMA Data Collection  (updated model — Cycle N+1)",
        sub="EMA items follow recommended_next_observation_predictors from Step 04",
        bc=B_DATA, fc=F_DATA, fontsize=8.2)

    arr(ax, Cx+4.25, y_ema2, Hx-3.25, y_rdy,
        label="new EMA series → Cycle N+1", color=E_CYCLE, lw=1.1, rad=0.0)

    # ── STAGE ANNOTATIONS (left margin) ──────────────────────────────────────
    for y_pos, lbl in [(y_complaint, "INPUT"), (y_s01, "01"), (y_s02, "02"),
                        (y_ema1, "EMA"), (y_s03, "03"), (y_s04, "04"),
                        (y_s05, "05"), (y_arts, "OUT"), (y_hist, "HIST"),
                        (y_ema2, "EMA+1")]:
        ax.text(2.8, y_pos, lbl, ha="center", va="center",
                fontsize=7, fontweight="bold", color=TEXT_LIGHT, style="italic")

    # light horizontal separators
    for y_sep in [y_s01-0.65, y_s02-0.65, y_ema1-0.55,
                  y_s03-0.70, y_s04-0.70, y_s05-0.70, y_arts-0.65]:
        ax.axhline(y_sep, xmin=0.04, xmax=0.84, color=BORDER_MID,
                   lw=0.4, linestyle=":", zorder=0)


    # thin outer frame
    LX = 2.3  # left x of frame (pulls in the left margin)
    for x0_, y0_, x1_, y1_ in [(LX, 0.5, FIG_W-0.5, 0.5),
                                  (FIG_W-0.5, 0.5, FIG_W-0.5, 33-0.5),
                                  (FIG_W-0.5, 33-0.5, LX, 33-0.5),
                                  (LX, 33-0.5, LX, 0.5)]:
        ax.plot([x0_, x1_], [y0_, y1_], color=BORDER_MID, lw=0.8, zorder=0)


    # ── SAVE ─────────────────────────────────────────────────────────────────
    out = Path(__file__).parent / "create_flowchart.png"
    fig.savefig(out, dpi=DPI, bbox_inches="tight",
                facecolor=BG, edgecolor="none")
    plt.close(fig)
    print(f"[PHOENIX] Saved: {out}")
    return out


if __name__ == "__main__":
    build()
