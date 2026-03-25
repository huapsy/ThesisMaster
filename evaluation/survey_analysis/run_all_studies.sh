#!/usr/bin/env bash
# ─────────────────────────────────────────────────────────────
# PHOENIX Survey Analysis — Run All Studies
# ─────────────────────────────────────────────────────────────
# Generates pseudodata (if not already present) and runs all
# 7 analysis scripts (00–06) sequentially.
#
# Usage:
#   cd /path/to/MASTERPROEF
#   bash evaluation/survey_analysis/run_all_studies.sh
# ─────────────────────────────────────────────────────────────

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"

# Use venv python if available
PYTHON="${REPO_ROOT}/.venv/bin/python"
if [ ! -f "$PYTHON" ]; then
    PYTHON="python3"
fi

echo "=== PHOENIX Survey Analysis: Run All Studies ==="
echo "Repo root : $REPO_ROOT"
echo "Python    : $PYTHON"
echo ""

export MPLCONFIGDIR="${MPLCONFIGDIR:-/tmp/phoenix-mpl}"
mkdir -p "$MPLCONFIGDIR"

# Step 0: Generate pseudodata
echo "[1/8] Generating pseudodata..."
"$PYTHON" "$SCRIPT_DIR/data/generate_pseudodata.py"
echo ""

# Step 1–7: Run each analysis script
SCRIPTS=(
    "00_momentary_impact_ranking_analysis.py"
    "01_operationalization_analysis.py"
    "02_initial_model_analysis.py"
    "03_treatment_target_ranking_analysis.py"
    "04_updated_model_analysis.py"
    "05_intervention_analysis.py"
    "06_holistic_analysis.py"
)

STEP=2
for SCRIPT in "${SCRIPTS[@]}"; do
    echo "[${STEP}/8] Running $SCRIPT ..."
    "$PYTHON" "$SCRIPT_DIR/utils/$SCRIPT"
    echo ""
    STEP=$((STEP + 1))
done

echo "=== All studies complete. Results saved in: ==="
echo "    $SCRIPT_DIR/results/"
