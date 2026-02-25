# Hierarchical Updating Algorithm (HUA) · PHOENIX Engine

The HUA is the **quantitative backbone** of PHOENIX. It feeds the Agentic Framework with data-driven evidence at every iterative cycle, bridging idiographic clinical data with the nomothetic ontology.

## Agent Roles

### Readiness Classifier Agent (`01_time_series_analysis/01_check_readiness/`)
- **Input**: participant EMA time-series
- **Output**: `readiness_report.json` — readiness score (0–100), analysis execution plan, stationarity diagnostics
- **Role**: determines whether the time-series has sufficient variance, length, and stationarity for network modelling; selects the downstream analysis path

### Network Time-Series Analyst Agent (`01_time_series_analysis/02_network_time_series_analysis/`)
- **Input**: EMA time-series + readiness plan
- **Models**: tv-gVAR (time-varying graphical VAR) · stationary gVAR · baseline
- **Output**: contemporaneous and temporal edge weights between symptom/predictor nodes
- **Role**: constructs the individual dynamic network used to infer predictor–criterion relationships

### Regular Time-Series Analyst (`01_time_series_analysis/02_regular_time_series_analysis/`)
- Non-network analyses (descriptive statistics, trend decomposition) for cases below network readiness threshold

### Impact Quantifier Agent (`02_hierarchical_update_ranking/01_momentary_impact_quantification/`)
- **Input**: network edge weights + criterion set
- **Output**: `impact_matrix.csv` — per-predictor impact coefficients across all criteria
- **Role**: quantifies the *momentary impact* of each predictor on each criterion, used by Stage 04 to adaptively weight idiographic evidence

---

## Readiness → Adaptive Weighting Chain

```
readiness_score (0–100)
   ↓  / 100  → readiness_0_1
idiographic_weight = clamp(0.30 + 0.50 · readiness_0_1)   [range: 0.30–0.80]
nomothetic_weight  = 1 − idiographic_weight                [range: 0.20–0.70]
```

As the participant accumulates EMA data and readiness improves, the engine shifts weight from population-level (nomothetic) to individual-level (idiographic) evidence.

---

## BFS Candidate Selector

Implemented in `utils/agentic_core/shared/target_refinement.py`.

**Scoring per ontology leaf path:**
```
total_score = 0.45·mapping_score
            + 0.25·HyDE_dense_score
            + 0.20·idiographic_anchor_score
            + 0.10·domain_bonus
```

**BFS Phases:**
1. `breadth_domain_coverage` — one top-scoring leaf per domain (ensures diversity)
2. `breadth_round_robin` — round-robin within domains (up to `3 × n_domains`)
3. `depth_refinement` — fill remaining slots by global descending score

---

## Execution

```bash
python evaluation/integrated_pipeline/run_pipeline.py --mode synthetic_v1
```

`readiness_report.json` includes an `analysis_execution_plan` field — downstream methods read this to maintain explicit, auditable method selection.

See [`src/README.md`](../../README.md) for the full multi-agent architecture overview.
