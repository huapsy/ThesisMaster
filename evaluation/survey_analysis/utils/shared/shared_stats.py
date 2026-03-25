"""
Shared statistical and visualization utilities for all survey analysis scripts.
"""

import numpy as np
import pandas as pd
import matplotlib
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
from matplotlib.font_manager import findfont, FontProperties
import scipy.stats as stats
import statsmodels.formula.api as smf
import json
import warnings
from pathlib import Path

warnings.filterwarnings("ignore")

# ---------------------------------------------------------------------------
# Color palette constants
# ---------------------------------------------------------------------------
PALETTE = {
    "primary": "#4f46e5",      # indigo  — PHOENIX / main
    "secondary": "#10b981",    # emerald — HCP / human / comparison
    "tertiary": "#f59e0b",     # amber   — third group / highlight
    "neutral": "#9ca3af",      # gray    — non-significant
    "ref_line": "#6b7280",     # mid-gray for reference lines
}

# Convenience aliases
COLOR_PHOENIX = PALETTE["primary"]
COLOR_HCP     = PALETTE["secondary"]
COLOR_AMBER   = PALETTE["tertiary"]
COLOR_GRAY    = PALETTE["neutral"]

# Dim color sets (used in studies 01/02/04)
DIM_COLORS = [
    "#4f46e5",  # indigo
    "#10b981",  # emerald
    "#f59e0b",  # amber
    "#ef4444",  # red
    "#8b5cf6",  # violet
    "#06b6d4",  # cyan
]

# ---------------------------------------------------------------------------
# Global rcParams for publication-quality figures
# ---------------------------------------------------------------------------
RCPARAMS = {
    "font.family": "DejaVu Sans",
    "font.size": 11,
    "axes.titlesize": 13,
    "axes.labelsize": 12,
    "xtick.labelsize": 10,
    "ytick.labelsize": 10,
    "axes.spines.top": False,
    "axes.spines.right": False,
    "figure.dpi": 150,
}


def apply_rcparams():
    """Apply publication-quality rcParams globally."""
    plt.rcParams.update(RCPARAMS)


# ---------------------------------------------------------------------------
# Font setup (kept for backward compat but DejaVu Sans is now the default)
# ---------------------------------------------------------------------------
def get_preferred_font():
    for font_name in ["Inter", "Arial", "DejaVu Sans"]:
        fp = FontProperties(family=font_name)
        path = findfont(fp, fallback_to_default=False)
        if path and font_name.lower() in path.lower():
            return font_name
    return "DejaVu Sans"


# Apply rcParams on import
apply_rcparams()


# ---------------------------------------------------------------------------
# Statistical helpers
# ---------------------------------------------------------------------------
def shapiro_wilk_test(values):
    """Run Shapiro-Wilk normality test. Returns (statistic, p_value, is_normal)."""
    if len(values) < 3:
        return None, None, True
    try:
        stat, p = stats.shapiro(values)
        return float(stat), float(p), bool(p > 0.05)
    except Exception:
        return None, None, True


def cohen_d(group1, group2):
    """Cohen's d for two independent groups."""
    n1, n2 = len(group1), len(group2)
    mean1, mean2 = np.mean(group1), np.mean(group2)
    var1, var2 = np.var(group1, ddof=1), np.var(group2, ddof=1)
    pooled_sd = np.sqrt(((n1 - 1) * var1 + (n2 - 1) * var2) / (n1 + n2 - 2))
    if pooled_sd == 0:
        return 0.0
    return float((mean1 - mean2) / pooled_sd)


def cohen_d_vs_null(values, null=2.5):
    """Cohen's d of a single sample vs a null value."""
    sd = np.std(values, ddof=1)
    return (np.mean(values) - null) / sd if sd > 0 else 0.0


def rank_biserial_r(U, n1, n2):
    """Rank-biserial r from Mann-Whitney U."""
    return float(1 - (2 * U) / (n1 * n2)) if (n1 * n2) > 0 else 0.0


def effect_size_r(z_stat, n_total):
    """Effect size r = Z / sqrt(N) for Mann-Whitney."""
    return float(z_stat / np.sqrt(n_total)) if n_total > 0 else 0.0


def ci_mean(values, confidence=0.95):
    """Confidence interval around mean (t-based)."""
    n = len(values)
    if n < 2:
        m = np.mean(values)
        return float(m), float(m), float(m)
    se = stats.sem(values)
    t_crit = stats.t.ppf((1 + confidence) / 2.0, df=n - 1)
    m = np.mean(values)
    return float(m), float(m - t_crit * se), float(m + t_crit * se)


def bootstrap_ci_mean(values, n_boot=2000, seed=42, confidence=0.95):
    """Bootstrap 95% CI for the mean."""
    rng = np.random.default_rng(seed)
    boot_means = [np.mean(rng.choice(values, size=len(values), replace=True))
                  for _ in range(n_boot)]
    lo = float(np.percentile(boot_means, (1 - confidence) / 2 * 100))
    hi = float(np.percentile(boot_means, (1 + confidence) / 2 * 100))
    return lo, hi


def bootstrap_cohend_ci(g1, g2, n_boot=2000, seed=42, confidence=0.95):
    """Bootstrap CI for Cohen's d."""
    rng = np.random.default_rng(seed)
    ds = []
    for _ in range(n_boot):
        s1 = rng.choice(g1, size=len(g1), replace=True)
        s2 = rng.choice(g2, size=len(g2), replace=True)
        ds.append(cohen_d(s1, s2))
    lo = float(np.percentile(ds, (1 - confidence) / 2 * 100))
    hi = float(np.percentile(ds, (1 + confidence) / 2 * 100))
    return lo, hi


def run_lme(df, dimension, group_col, random_effect_col, reference="expert_group"):
    """
    Fit a linear mixed effects model:
      dimension ~ source + (1|random_effect_col)
    Returns result dict with key statistics.
    """
    df = df.copy()
    levels = df[group_col].unique().tolist()
    if reference in levels:
        levels = [reference] + [l for l in levels if l != reference]

    df["source_code"] = pd.Categorical(df[group_col], categories=levels)
    formula = f"{dimension} ~ C({group_col}, Treatment(reference='{reference}'))"
    try:
        model = smf.mixedlm(
            formula,
            data=df,
            groups=df[random_effect_col],
        )
        result = model.fit(reml=True, method="lbfgs")

        params = result.params
        bse = result.bse
        tvalues = result.tvalues
        pvalues = result.pvalues

        source_key = [k for k in params.index if group_col in k and "Intercept" not in k]
        if not source_key:
            source_key = [k for k in params.index if k != "Intercept" and "Group Var" not in k]

        if source_key:
            key = source_key[0]
            coef = float(params[key])
            se = float(bse[key])
            t_val = float(tvalues[key])
            p_val = float(pvalues[key])
        else:
            coef, se, t_val, p_val = 0.0, 0.0, 0.0, 1.0

        ci_lo = coef - 1.96 * se
        ci_hi = coef + 1.96 * se

        try:
            blups = result.random_effects
            blup_vals = [float(v.values[0]) for v in blups.values()]
        except Exception:
            blup_vals = []

        return {
            "test": "LME",
            "coefficient": coef,
            "se": se,
            "t_value": t_val,
            "p_value": p_val,
            "ci_lower": ci_lo,
            "ci_upper": ci_hi,
            "blup_values": blup_vals,
            "converged": bool(result.converged),
        }
    except Exception as e:
        return {
            "test": "LME",
            "error": str(e),
            "coefficient": 0.0,
            "se": 0.0,
            "t_value": 0.0,
            "p_value": 1.0,
            "ci_lower": 0.0,
            "ci_upper": 0.0,
            "blup_values": [],
            "converged": False,
        }


def run_mann_whitney(g1, g2):
    """Mann-Whitney U test for two groups. Returns result dict."""
    try:
        stat, p = stats.mannwhitneyu(g1, g2, alternative="two-sided")
        n = len(g1) + len(g2)
        z = stats.norm.ppf(p / 2)
        r = abs(effect_size_r(z, n))
        return {
            "test": "Mann-Whitney U",
            "statistic": float(stat),
            "z_approx": float(z),
            "p_value": float(p),
            "effect_size_r": r,
            "n_total": n,
        }
    except Exception as e:
        return {
            "test": "Mann-Whitney U",
            "error": str(e),
            "statistic": 0.0,
            "p_value": 1.0,
            "effect_size_r": 0.0,
        }


def bonferroni_correct(p_values):
    """Apply Bonferroni correction to a list of p-values."""
    n = len(p_values)
    return [min(p * n, 1.0) for p in p_values]


def _candidate_vc_formula(variance_components):
    if not variance_components:
        return None
    vc_formula = {
        name: f"0 + C({column})"
        for name, column in variance_components.items()
        if column
    }
    return vc_formula or None


def fit_crossed_mixedlm(data, formula, effect_term, candidates):
    """
    Try a sequence of mixed-model specifications and return the first converged fit.

    Parameters
    ----------
    data : pd.DataFrame
    formula : str
    effect_term : str
        Name of the fixed-effect coefficient to extract.
    candidates : list[dict]
        Each candidate requires a ``label`` and ``group_col`` and can optionally
        include ``re_formula`` and ``variance_components``.
    """
    errors = []
    for candidate in candidates:
        group_col = candidate.get("group_col")
        if group_col not in data.columns or data[group_col].nunique() < 2:
            continue
        vc_formula = _candidate_vc_formula(candidate.get("variance_components"))
        try:
            model = smf.mixedlm(
                formula,
                data=data,
                groups=data[group_col],
                re_formula=candidate.get("re_formula"),
                vc_formula=vc_formula,
            ).fit(reml=True, method="lbfgs")
            coef = float(model.params.get(effect_term, 0.0))
            se = float(model.bse.get(effect_term, 0.0))
            residuals = np.asarray(model.resid, dtype=float)
            residuals = residuals[np.isfinite(residuals)]
            if residuals.size >= 3:
                try:
                    shapiro_w, shapiro_p = stats.shapiro(residuals[:5000])
                    shapiro_w = float(shapiro_w)
                    shapiro_p = float(shapiro_p)
                except Exception:
                    shapiro_w = np.nan
                    shapiro_p = np.nan
            else:
                shapiro_w = np.nan
                shapiro_p = np.nan
            return {
                "method": candidate["label"],
                "group_col": group_col,
                "variance_components": candidate.get("variance_components", {}),
                "coefficient": coef,
                "se": se,
                "ci_lower": coef - 1.96 * se,
                "ci_upper": coef + 1.96 * se,
                "p_value": float(model.pvalues.get(effect_term, 1.0)),
                "converged": bool(model.converged),
                "shapiro_w": shapiro_w,
                "shapiro_p": shapiro_p,
            }
        except Exception as exc:
            errors.append(f"{candidate['label']}: {exc}")
    return {
        "method": "No converged mixed model",
        "group_col": None,
        "variance_components": {},
        "coefficient": 0.0,
        "se": 0.0,
        "ci_lower": 0.0,
        "ci_upper": 0.0,
        "p_value": 1.0,
        "converged": False,
        "shapiro_w": np.nan,
        "shapiro_p": np.nan,
        "error": " | ".join(errors) if errors else "No valid candidate model.",
    }


def p_to_stars(p):
    """Convert p-value to significance stars."""
    if p < 0.001:
        return "***"
    elif p < 0.01:
        return "**"
    elif p < 0.05:
        return "*"
    else:
        return "ns"


def interpret_result(dimension, test_result, group_ref, group_test, adj_p, is_lme=True):
    """Generate interpretation string."""
    if is_lme:
        coef = test_result.get("coefficient", 0)
        direction = "outperforms" if coef > 0 else "underperforms relative to"
        actor = group_test if coef > 0 else group_ref
        other = group_ref if coef > 0 else group_test
        return (
            f"{actor} {direction} {other} on {dimension} "
            f"(p_adj={adj_p:.4f}, coef={coef:.3f})"
        )
    else:
        r = test_result.get("effect_size_r", 0)
        return (
            f"Non-parametric comparison on {dimension}: "
            f"p_adj={adj_p:.4f}, r={r:.3f}"
        )


# ---------------------------------------------------------------------------
# Visualization helpers — publication-quality
# ---------------------------------------------------------------------------

def add_significance_bracket(ax, x1, x2, y, p_value, h=0.15, color="black", lw=1.2):
    """Draw a significance bracket between x1 and x2 at height y."""
    stars = p_to_stars(p_value)
    ax.plot([x1, x1, x2, x2], [y, y + h, y + h, y], lw=lw, color=color)
    ax.text(
        (x1 + x2) / 2,
        y + h + 0.02,
        stars,
        ha="center",
        va="bottom",
        fontsize=12,
        color=color,
        fontweight="bold" if stars != "ns" else "normal",
    )


def violin_with_scatter(ax, data_dict, title, ylabel,
                        colors=None, p_value=None, adj_p=None,
                        ref_line=None, ref_label=None,
                        ylim=None, add_mean_sd=True):
    """
    Publication-quality violin plot with jittered scatter and optional
    mean ± SD markers, significance bracket, and reference line.

    Parameters
    ----------
    ax           : matplotlib Axes
    data_dict    : {label: array_of_values}
    title        : str
    ylabel       : str
    colors       : list of hex strings (defaults to PALETTE primary/secondary/tertiary)
    p_value      : float or None — raw p value for bracket
    adj_p        : float or None — adjusted p value (used instead of p_value if given)
    ref_line     : float or None — y position for a horizontal reference line
    ref_label    : str or None — label for reference line
    ylim         : tuple or None
    add_mean_sd  : bool — overlay mean ± SD error bar
    """
    apply_rcparams()
    labels = list(data_dict.keys())
    all_data = [np.array(data_dict[l], dtype=float) for l in labels]
    positions = list(range(1, len(labels) + 1))

    if colors is None:
        default_cycle = [PALETTE["primary"], PALETTE["secondary"], PALETTE["tertiary"]]
        colors = [default_cycle[i % len(default_cycle)] for i in range(len(labels))]

    # Violin bodies
    parts = ax.violinplot(all_data, positions=positions, showmedians=False,
                          showextrema=False, widths=0.65)
    for i, pc in enumerate(parts["bodies"]):
        pc.set_facecolor(colors[i])
        pc.set_edgecolor(colors[i])
        pc.set_alpha(0.30)

    # Jittered scatter
    rng_jit = np.random.default_rng(42)
    for i, (vals, pos) in enumerate(zip(all_data, positions)):
        jitter = rng_jit.uniform(-0.10, 0.10, size=len(vals))
        ax.scatter(
            np.full(len(vals), pos) + jitter,
            vals,
            color=colors[i],
            alpha=0.55,
            s=18,
            zorder=3,
            edgecolors="white",
            linewidths=0.5,
        )

    # Mean ± SD markers
    if add_mean_sd:
        for i, (vals, pos) in enumerate(zip(all_data, positions)):
            m = np.mean(vals)
            sd = np.std(vals, ddof=1)
            ax.plot(pos, m, marker="D", color=colors[i], markersize=7,
                    markeredgecolor="white", markeredgewidth=1.2, zorder=5)
            ax.errorbar(pos, m, yerr=sd, fmt="none", color=colors[i],
                        capsize=5, capthick=1.5, elinewidth=1.5, zorder=4)

    # Median tick (short horizontal line)
    for i, (vals, pos) in enumerate(zip(all_data, positions)):
        med = np.median(vals)
        ax.plot([pos - 0.10, pos + 0.10], [med, med],
                color="white", lw=2.0, zorder=6)

    # Reference line
    if ref_line is not None:
        ax.axhline(ref_line, color=PALETTE["ref_line"], linestyle="--",
                   linewidth=1.0, alpha=0.8,
                   label=ref_label if ref_label else f"y = {ref_line}")

    # Significance bracket (only for exactly 2 groups)
    if p_value is not None and len(positions) == 2:
        p_show = adj_p if adj_p is not None else p_value
        y_max = max(max(d) for d in all_data if len(d) > 0)
        y_range = y_max - min(min(d) for d in all_data if len(d) > 0)
        y_bracket = y_max + y_range * 0.07
        h_bracket = y_range * 0.05
        add_significance_bracket(ax, positions[0], positions[1],
                                 y_bracket, p_show, h=h_bracket)

    ax.set_xticks(positions)
    ax.set_xticklabels(labels, fontsize=10)
    ax.set_ylabel(ylabel)
    ax.set_title(title, fontweight="bold", pad=12)
    ax.set_xlim(0.4, len(labels) + 0.6)
    if ylim is not None:
        ax.set_ylim(ylim)

    return ax


def horizontal_bar_chart(ax, labels, means, sds, sig_flags,
                         title, xlabel,
                         ref_line=None, ref_label=None,
                         primary_color=None, neutral_color=None):
    """
    Horizontal bar chart sorted by mean value (descending), with error bars,
    value labels, and optional reference line.

    sig_flags : list of bool — True = significant (primary color), False = gray
    """
    apply_rcparams()
    if primary_color is None:
        primary_color = PALETTE["primary"]
    if neutral_color is None:
        neutral_color = PALETTE["neutral"]

    # Sort descending by mean
    order = np.argsort(means)[::-1]
    sorted_labels = [labels[i] for i in order]
    sorted_means  = [means[i] for i in order]
    sorted_sds    = [sds[i] for i in order]
    sorted_sig    = [sig_flags[i] for i in order]

    colors = [primary_color if s else neutral_color for s in sorted_sig]
    y_pos = np.arange(len(sorted_labels))

    ax.barh(y_pos, sorted_means, xerr=sorted_sds,
            color=colors, alpha=0.82, capsize=4,
            error_kw={"elinewidth": 1.2, "capthick": 1.2},
            height=0.65)

    # Value labels
    for i, (m, sd) in enumerate(zip(sorted_means, sorted_sds)):
        ax.text(m + sd + 0.05, i, f"{m:.2f}", va="center", fontsize=9,
                color="#374151")

    # Reference line
    if ref_line is not None:
        ax.axvline(ref_line, color=PALETTE["ref_line"], linestyle="--",
                   linewidth=1.0, alpha=0.8,
                   label=ref_label if ref_label else f"x = {ref_line}")
        ax.legend(fontsize=9)

    ax.set_yticks(y_pos)
    ax.set_yticklabels(sorted_labels, fontsize=10)
    ax.set_xlabel(xlabel)
    ax.set_title(title, fontweight="bold", pad=12)
    ax.invert_yaxis()

    return ax


def forest_plot(ax, dimensions, effects, ci_lowers, ci_uppers, title,
                xlabel="Effect Size", ref_line=0):
    """Horizontal forest plot of effect sizes with CIs."""
    y_pos = list(range(len(dimensions)))
    colors = [PALETTE["primary"] if e >= 0 else PALETTE["secondary"] for e in effects]

    for i, (d, e, lo, hi, c) in enumerate(
        zip(dimensions, effects, ci_lowers, ci_uppers, colors)
    ):
        ax.plot([lo, hi], [i, i], color=c, linewidth=2, solid_capstyle="round")
        ax.plot(e, i, "o", color=c, markersize=8, zorder=5)
        ax.text(
            hi + abs(hi - lo) * 0.05 + 0.02,
            i,
            f"{e:.2f} [{lo:.2f}, {hi:.2f}]",
            va="center",
            fontsize=8,
            color=c,
        )

    ax.axvline(ref_line, color="black", linestyle="--", linewidth=1, alpha=0.6)
    ax.set_yticks(y_pos)
    ax.set_yticklabels(dimensions, fontsize=10)
    ax.set_xlabel(xlabel)
    ax.set_title(title, fontweight="bold", pad=12)
    ax.invert_yaxis()
    return ax


def random_effects_histogram(ax, blup_values, title="Random Effects (BLUPs)"):
    """Histogram of BLUP estimates."""
    if not blup_values:
        ax.text(0.5, 0.5, "No BLUPs available", transform=ax.transAxes,
                ha="center", va="center")
        ax.set_title(title, fontweight="bold")
        return ax

    ax.hist(blup_values, bins=min(len(blup_values), 15), color=PALETTE["primary"],
            edgecolor="white", alpha=0.75)
    ax.axvline(0, color="#ef4444", linestyle="--", linewidth=1, alpha=0.7)
    ax.set_xlabel("BLUP Estimate")
    ax.set_ylabel("Count")
    ax.set_title(title, fontweight="bold", pad=12)
    return ax


def correlation_heatmap(ax, df, dimensions, title="Correlation Heatmap"):
    """Pearson correlation heatmap of dimensions."""
    sub = df[dimensions].dropna()
    corr = sub.corr(method="pearson")

    cmap = plt.get_cmap("RdBu_r")
    im = ax.imshow(corr.values, cmap=cmap, vmin=-1, vmax=1, aspect="auto")
    plt.colorbar(im, ax=ax, shrink=0.8)

    n = len(dimensions)
    ax.set_xticks(range(n))
    ax.set_yticks(range(n))
    short_labels = [d[:15] for d in dimensions]
    ax.set_xticklabels(short_labels, rotation=40, ha="right", fontsize=8)
    ax.set_yticklabels(short_labels, fontsize=8)

    for i in range(n):
        for j in range(n):
            val = corr.values[i, j]
            text_color = "white" if abs(val) > 0.6 else "black"
            ax.text(j, i, f"{val:.2f}", ha="center", va="center",
                    fontsize=8, color=text_color)

    ax.set_title(title, fontweight="bold", pad=12)
    return ax


def publication_heatmap(ax, data_matrix, row_labels, col_labels, title,
                        cmap="RdYlGn", vmin=0.0, vmax=1.0,
                        colorbar_label="Normalized Score (0-1)"):
    """
    Diverging heatmap centred at 0.5, with cell annotations and a colorbar.
    Used in study 06.
    """
    apply_rcparams()
    im = ax.imshow(data_matrix, aspect="auto", cmap=cmap, vmin=vmin, vmax=vmax)
    cbar = plt.colorbar(im, ax=ax, shrink=0.85, pad=0.02)
    cbar.set_label(colorbar_label, fontsize=10)

    n_rows, n_cols = data_matrix.shape
    ax.set_xticks(np.arange(n_cols))
    ax.set_yticks(np.arange(n_rows))
    ax.set_xticklabels([c.replace("_", "\n") for c in col_labels], fontsize=9)
    ax.set_yticklabels(row_labels, fontsize=9)

    for i in range(n_rows):
        for j in range(n_cols):
            val = data_matrix[i, j]
            if not np.isnan(val):
                # Choose text color for contrast
                text_color = "white" if val < 0.35 or val > 0.80 else "black"
                ax.text(j, i, f"{val:.3f}", ha="center", va="center",
                        fontsize=8, color=text_color, fontweight="bold")

    ax.set_title(title, fontweight="bold", pad=12)
    return ax


def violin_gradient_scatter(ax, data_dict, title, ylabel, p_value=None,
                             adj_p=None, cmap="viridis"):
    """
    Backward-compat wrapper: Violin plot with gradient-colored scatter.
    Calls violin_with_scatter internally.
    """
    return violin_with_scatter(ax, data_dict, title, ylabel,
                               p_value=p_value, adj_p=adj_p)


def boxwhisker_with_points(ax, data_dict, title, ylabel, cmap="viridis"):
    """Box-whisker plot with individual points (backward compat)."""
    labels = list(data_dict.keys())
    all_data = [np.array(data_dict[l], dtype=float) for l in labels]
    positions = list(range(1, len(labels) + 1))

    bp = ax.boxplot(all_data, positions=positions, patch_artist=True,
                    widths=0.4, notch=False)
    for i, patch in enumerate(bp["boxes"]):
        patch.set_facecolor(DIM_COLORS[i % len(DIM_COLORS)])
        patch.set_alpha(0.5)
    for median in bp["medians"]:
        median.set_color("black")
        median.set_linewidth(2)

    rng_jit = np.random.default_rng(42)
    for i, (vals, pos) in enumerate(zip(all_data, positions)):
        jitter = rng_jit.uniform(-0.12, 0.12, size=len(vals))
        ax.scatter(
            np.full(len(vals), pos) + jitter,
            vals,
            color=DIM_COLORS[i % len(DIM_COLORS)],
            alpha=0.5,
            s=12,
            zorder=3,
        )

    ax.set_xticks(positions)
    ax.set_xticklabels(labels, fontsize=10)
    ax.set_ylabel(ylabel)
    ax.set_title(title, fontweight="bold", pad=12)
    return ax


def save_figure(fig, path, dpi=300):
    """Save figure with consistent settings."""
    fig.patch.set_facecolor("white")
    fig.savefig(path, dpi=dpi, bbox_inches="tight", facecolor="white")
    plt.close(fig)
    print(f"  Saved figure: {path}")


# ---------------------------------------------------------------------------
# Report helpers
# ---------------------------------------------------------------------------
def build_dim_result(dimension, normality, lme_or_mw, adj_p, is_lme=True,
                     cohen_d_val=None, cohen_d_ci=None, group_ref="expert",
                     group_test="LLM"):
    """Build a standardized result dict for one dimension."""
    res = {
        "dimension": dimension,
        "normality": {
            "shapiro_stat": normality[0],
            "shapiro_p": normality[1],
            "is_normal": normality[2],
        },
        "test_used": lme_or_mw.get("test", "unknown"),
        "p_value": lme_or_mw.get("p_value", None),
        "p_value_adjusted": adj_p,
        "interpretation": interpret_result(
            dimension, lme_or_mw, group_ref, group_test, adj_p, is_lme=is_lme
        ),
    }
    if is_lme:
        res["coefficient"] = lme_or_mw.get("coefficient")
        res["se"] = lme_or_mw.get("se")
        res["t_value"] = lme_or_mw.get("t_value")
        res["ci_95"] = [lme_or_mw.get("ci_lower"), lme_or_mw.get("ci_upper")]
        if cohen_d_val is not None:
            res["effect_size"] = {"type": "Cohen's d", "value": cohen_d_val,
                                   "ci_95": cohen_d_ci}
    else:
        res["statistic"] = lme_or_mw.get("statistic")
        res["effect_size"] = {"type": "r", "value": lme_or_mw.get("effect_size_r")}
    return res


def save_json_report(report, path):
    """Save JSON report."""
    with open(path, "w") as f:
        json.dump(report, f, indent=2, default=str)
    print(f"  Saved JSON report: {path}")


def save_markdown_report(report, path):
    """Generate and save a markdown report from a structured report dict."""
    lines = []
    meta = report.get("metadata", {})
    lines.append(f"# {meta.get('study_name', 'Study Report')}\n")
    lines.append(f"**Study:** {meta.get('study_id', '')}  ")
    lines.append(f"**N:** {meta.get('n', '')}  ")
    lines.append(f"**Design:** {meta.get('design', '')}  ")
    lines.append(f"**Date:** {meta.get('date', '')}  \n")

    lines.append("## Statistical Results\n")
    for dim_res in report.get("results", []):
        dim = dim_res.get("dimension", "")
        lines.append(f"### {dim}\n")
        lines.append(f"- **Test:** {dim_res.get('test_used', '')}  ")
        p_raw = dim_res.get("p_value")
        if p_raw is not None:
            lines.append(f"- **p-value:** {p_raw:.4f}  ")
        adj_p = dim_res.get("p_value_adjusted")
        if adj_p is not None:
            lines.append(f"- **Adjusted p (Bonferroni):** {adj_p:.4f}  ")
        if "coefficient" in dim_res:
            lines.append(f"- **Coefficient (LLM vs ref):** {dim_res['coefficient']:.3f}  ")
            ci = dim_res.get("ci_95", [None, None])
            if ci[0] is not None:
                lines.append(f"- **95% CI:** [{ci[0]:.3f}, {ci[1]:.3f}]  ")
        if "effect_size" in dim_res:
            es = dim_res["effect_size"]
            es_val = es.get("value")
            es_str = f"{es_val:.3f}" if es_val is not None else "N/A"
            lines.append(
                f"- **Effect size ({es.get('type', '')}):** {es_str}  "
            )
        norm = dim_res.get("normality", {})
        sw_p = norm.get("shapiro_p")
        if sw_p is not None:
            lines.append(
                f"- **Shapiro-Wilk p:** {sw_p:.4f} "
                f"({'normal' if norm.get('is_normal') else 'non-normal'})  "
            )
        lines.append(f"\n**Interpretation:** {dim_res.get('interpretation', '')}  \n")

    with open(path, "w") as f:
        f.write("\n".join(lines))
    print(f"  Saved Markdown report: {path}")
