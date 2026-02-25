# PHOENIX Engine — Multi-Agent System (`src/`)

The **PHOENIX Engine** is a research-grade **pre-determined sequential Multi-Agent System** for personalised mental-health treatment plan generation.

| Property | Value |
|---|---|
| **Entry point** | Free-text mental health complaint (not raw time-series data) |
| **No orchestrator** | Five-stage sequence is fixed; each stage's output deterministically feeds the next |
| **Five ontologies** | CRITERION · PREDICTOR · PERSON · CONTEXT · HAPA — stable structural constraints across cycles |
| **Iterative** | Artefacts from cycle N seed cycle N+1 via the history ledger |

---

## Architecture

![PHOENIX Multi-Agent System](./overview/create_flowchart.png)

*Full Mermaid flowchart and design principles: [`overview/README.md`](./overview/README.md) · Regenerate PNG: `python src/overview/create_flowchart.py`*

---

## Agents & Roles

### Input

| Component | Fields |
|---|---|
| Free-text complaint | `complaint_text` · `person_text` · `context_text` (pseudoprofile) |

### Stage 01 — Criterion Operationalization

| Agent | Script | Role |
|---|---|---|
| **Criterion Operationalization Agent** | `01_OperationalizationMentalHealthProblem/` | HTSSF fusion (embedding + BM25 + token-overlap + fuzzy) → LLM adjudication (re-rank top-50) → **single CRITERION leaf** |

### Stage 02 — Initial Observation Model

| Agent | Prompts / Script | Role |
|---|---|---|
| **Initial Observation Model Constructor** | `02_ConstructionInitialObservationModel/utils/01_construct_observation_model.py` | HyDE-based predictor RAG · bipartite criterion × predictor network · PREDICTOR ontology mapping |
| **Initial Model Critic** | `step02_initial_model_critic_*` | `predictor_grounding · criterion_continuity · ontology_strictness · evidence_quality` → **PASS / REVISE** (max 2) |

### EMA Data Collection *(post-model)*

> EMA measurement items are derived from Step 02's predictor selection. Data collection happens **after** the initial model is approved — not upfront.

### Hierarchical Updating Algorithm (HUA)

| Agent | Module | Role |
|---|---|---|
| **Readiness Classifier** | `HUA/01_time_series_analysis/01_check_readiness/` | Variance · stationarity · n-obs → `readiness_report.json` · selects tier: tv-gVAR / gVAR / baseline |
| **Network Time-Series Analyst** | `HUA/01_time_series_analysis/02_network_time_series_analysis/` | Fits tv-gVAR / stationary gVAR → contemporaneous & temporal edge weights |
| **Momentary Impact Quantifier** | `HUA/02_hierarchical_update_ranking/` | Predictor impact coefficients → `impact_matrix.csv` |
| **BFS Candidate Selector** | `utils/agentic_core/shared/target_refinement.py` | `score = 0.45·mapping + 0.25·HyDE + 0.20·idiographic_anchor + 0.10·domain_bonus` |

### Stages 03 & 04 — Target Identification + Model Update *(co-located)*

> Steps 03 and 04 run sequentially inside **one script**: `03_TreatmentTargetIdentification/01_prepare_targets_from_impact.py`.

| Agent | Prompts | Role |
|---|---|---|
| **Treatment Target Identifier** | `step03_target_selection_*` | Integrates BFS candidates + impact + network + initial model + profile text → `ranked_predictors` + `recommended_targets` (≤ 3) |
| **Target Selection Critic** | `step03_target_selection_critic_*` | `predictor_grounding · evidence_quality · safety_considerations · ontology_strictness` → **PASS / REVISE** (max 2) |
| **Update Observation Model Actor** | `step04_observation_update_*` | `fuse_updated_model_matrix`: `idiographic_weight = clamp(0.30 + 0.50·readiness)` → `refined_predictor_shortlist` + `recommended_next_observation_predictors` |
| **Updated Model Critic** | `step04_observation_update_critic_*` | `predictor_grounding · criterion_continuity · bfs_depth_balance · fusion_consistency` → **PASS / REVISE** (max 2) |

### Stage 05 — HAPA-based Intervention

| Agent | Script | Role |
|---|---|---|
| **Generate HAPA-based Intervention Actor** | `05_TranslationDigitalIntervention/01_generate_hapa_digital_intervention.py` | Barrier scoring (`0.60·predictor + 0.20·profile + 0.15·context + 0.05·complaint`) · coping selection · phased EMA delivery plan |
| **Intervention Critic** | `step05_hapa_intervention_critic_*` | `reasoning_quality·0.17 · evidence_grounding·0.21 · hapa_consistency·0.16 · medical_safety·0.16` → **PASS / REVISE** (max 2) |

### Cycle Persistence

| Component | Script | Role |
|---|---|---|
| **History Ledger** | `04_ConstructionUpdatedObservationModel/01_run_updated_model_cycle.py` | Appends `profile_history.jsonl`; `cycle_summary.json`; `previous_cycle_scores` feed BFS stability bonus in cycle N+1 |

---

## Iterative Cycle

```
Cycle N
 ├─ [01] Criterion Operationalization Agent  →  CRITERION leaf
 ├─ [02] Initial Observation Model Constructor  ⟺  Initial Model Critic
 ├─  ·· EMA Data Collection  (items from Step 02 predictor set)
 ├─  ·· HUA: Readiness → Network Analysis → Impact Quantification
 ├─  ·· BFS Candidate Selection
 ├─ [03] Treatment Target Identifier  ⟺  Target Critic       ┐ co-located
 ├─ [04] Update Observation Model Actor  ⟺  Updated Model Critic  ┘
 │           idiographic_weight = clamp(0.30 + 0.50·readiness)
 ├─ [05] Generate HAPA-based Intervention Actor  ⟺  Intervention Critic
 └─  →   Artifacts  →  History Ledger  →  EMA (updated model)  →  Cycle N+1
```

**Shared infrastructure (all stages):**
- `guardrail.py` — `decision_from_score(composite, threshold) → PASS | REVISE`
- `llm_runtime.py` — retry, JSON-repair, model fallback, token budget enforcement
- `contracts/` — Pydantic schema validation on every stage output
- Ontology hard-enforcement on all predictor / barrier / coping paths before persistence

---

## Directory Structure

```
src/
├── SystemComponents/
│   ├── Agentic_Framework/          # LLM stages 01–05 (generator + critic each)
│   ├── Hierarchical_Updating_Algorithm/  # Readiness → network → impact quantification
│   └── PHOENIX_ontology/           # CRITERION · PREDICTOR · PERSON · CONTEXT · HAPA
├── overview/
│   ├── README.md                   # This file — architecture overview + Mermaid diagram
│   ├── create_flowchart.py         # Generates create_flowchart.png
│   └── create_flowchart.png        # Full architecture diagram
└── utils/
    ├── agentic_core/
    │   ├── shared/                 # guardrail · feasibility · BFS (target_refinement) · llm_runtime
    │   └── prompts/                # Versioned prompt registry (prompts_manifest.json)
    └── official/                   # Preparatory scripts
```

---

## Execution

```bash
# Single cycle
python evaluation/integrated_pipeline/run_pipeline.py --mode synthetic_v1

# Multi-cycle with history (N cycles)
python evaluation/integrated_pipeline/run_pipeline.py --mode synthetic_v1 --cycles N

# Resume from prior run
python evaluation/integrated_pipeline/run_pipeline.py \
    --mode synthetic_v1 --cycles N --resume-from-run <run_id>
```

> Do not invoke individual stage scripts directly — the pipeline script ensures artefact path consistency across cycles.
