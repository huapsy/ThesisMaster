# PHOENIX Engine -- Core Architecture (`src/`)

The **PHOENIX Engine** is a research-grade **DAG-orchestrated multi-agent system** for personalized mental-health treatment plan generation. The system uses a directed acyclic graph (DAG) to manage stage dependencies, enabling parallel execution where possible and enforcing critic-actor quality gates at each stage boundary.

| Property | Value |
|---|---|
| **Entry point** | Free-text mental health complaint |
| **Orchestrator** | DAG-based (`src/backend/orchestrator.py`) with topological scheduling and parallel execution |
| **Five ontologies** | CRITERION, PREDICTOR, PERSON, CONTEXT, HAPA -- stable structural constraints across cycles |
| **Iterative** | Artifacts from cycle N seed cycle N+1 via the history ledger |
| **Quality gates** | Critic-actor loops with adaptive threshold relaxation and diminishing-returns detection |

---

## DAG Architecture

The pipeline consists of 12 stages organized as a DAG. The orchestrator identifies parallel execution groups automatically:

```
Group 1: [01] Complaint Operationalization
Group 2: [02] Initial Observation Model
Group 3: [03] Pseudodata Generation
Group 4: [04a] Readiness Check
Group 5: [04b] Network Time-Series Analysis
Group 6: [04c] Momentary Impact Quantification
Group 7: [05] Treatment Target ID  +  [09] Impact Visualization (parallel)
Group 8: [06] Updated Observation Model
Group 9: [07] HAPA Digital Intervention
Group 10: [08] Treatment Communication  +  [10] Research Reporting (parallel)
```

**Key design**: stages 05 and 09 execute in parallel (both depend on 04c but not on each other), and stages 08 and 10 execute in parallel (both depend on 07 but not on each other).

![PHOENIX Multi-Agent System](./backend/overview/create_flowchart.png)

---

## Agents and Roles

### Stage 01 -- Criterion Operationalization

| Agent | Method |
|---|---|
| **Complaint Decomposition Actor** | Always-on LLM decomposition into current, changeable complaint variables before ontology grounding |
| **Step 01 Local Critic** | Structured LLM critic over `schema_validity`, `coverage_grounding`, `atomicity_nonoverlap`, `granularity_fit`, `current_actionability` |
| **Criterion Operationalization Agent** | HTSSF fusion (dense embedding + BM25 + token-overlap + fuzzy) + optional final LLM leaf adjudication -> single CRITERION leaf |

### Stage 02 -- Initial Observation Model

| Agent | Role |
|---|---|
| **Initial Model Constructor** | HyDE-based predictor RAG, bipartite criterion x predictor network |
| **Initial Model Critic** | `predictor_grounding`, `criterion_continuity`, `ontology_strictness`, `evidence_quality` -> PASS/REVISE |

### Stages 04a-04c -- Hierarchical Updating Algorithm (HUA)

| Agent | Role |
|---|---|
| **Readiness Classifier** | Stationarity (ADF/KPSS), collinearity, effective sample size -> tier selection |
| **Network Time-Series Analyst** | tv-gVAR, stationary gVAR, partial correlations (Ledoit-Wolf) |
| **Momentary Impact Quantifier** | Leave-one-predictor-out MSE delta + coefficient magnitude |
| **BFS Candidate Selector** | `score = 0.45*mapping + 0.25*HyDE + 0.20*idiographic_anchor + 0.10*domain_bonus` |

### Stages 05-06 -- Target Identification + Model Update

| Agent | Role |
|---|---|
| **Treatment Target Identifier** | BFS candidates + impact + network -> ranked predictors + recommended targets (max 3) |
| **Target Selection Critic** | Safety, domain boundary, evidence quality -> PASS/REVISE |
| **Update Observation Model Actor** | `idiographic_weight = clamp(0.30 + 0.50 * readiness)` -> refined predictor shortlist |
| **Updated Model Critic** | Lineage consistency, fusion balance -> PASS/REVISE |

### Stage 07 -- HAPA-based Intervention

| Agent | Role |
|---|---|
| **HAPA Intervention Mapper** | Barrier scoring (0.60 predictor + 0.20 profile + 0.15 context + 0.05 complaint), coping selection |
| **Intervention Critic** | reasoning_quality (0.17), evidence_grounding (0.21), hapa_consistency (0.16), medical_safety (0.16) -> PASS/REVISE |

---

## Critic-Actor Quality Gates

All critic-gated stages use adaptive revision with two stopping conditions:

1. **Threshold met**: `composite_score >= adaptive_threshold` (threshold relaxes by 0.02 per revision)
2. **Diminishing returns**: score delta < 0.02 between consecutive revisions

Default configuration: `max_revisions=2`, `pass_threshold=0.74`.

---

## Iterative Cycle

```
Cycle N
 |-- [01] Criterion Operationalization -> CRITERION leaf
 |-- [02] Initial Observation Model <-> Critic
 |-- [03] Pseudodata Generation (EMA items from Step 02)
 |-- [04a-c] HUA: Readiness -> Network -> Impact
 |-- [05] Treatment Target ID <-> Critic
 |-- [06] Updated Observation Model <-> Critic
 |-- [07] HAPA Intervention <-> Critic
 |-- [08-10] Communication + Visualization + Reporting (parallel)
 +-- Artifacts -> History Ledger -> Cycle N+1
```

---

## Directory Structure

```
src/
├── backend/
│   ├── orchestrator.py                # DAG orchestrator (PipelineDAG, CriticActorLoop, PipelineOrchestrator)
│   ├── overview/                      # Architecture diagrams and Mermaid flowcharts
│   ├── SystemComponents/              # Agentic framework, HUA, intervention components, ontologies
│   └── utils/                         # Shared agentic runtime, prompts, contracts, feasibility assets
├── frontend/
│   ├── app.py                         # Flask entry point (port 5050)
│   └── phoenix_frontend/
│       ├── routes/                    # UI + API endpoints (14 REST + 3 UI routes)
│       ├── services/                  # PhoenixService, SessionStore, JobManager, CohortService
│       ├── static/                    # CSS design system + client-side JavaScript
│       └── templates/                 # Jinja2 templates (wizard-style pipeline UI)
├── __init__.py                        # Package root for `src.frontend` and `src.backend`
└── README.md                          # Architecture overview for the `src/` tree
```

---

## Shared Infrastructure

- `guardrail.py` -- `decision_from_score(composite, threshold) -> PASS | REVISE`
- `llm_runtime.py` -- retry, JSON-repair, model fallback, token budget enforcement
- `contracts/` -- Pydantic schema validation on every stage output
- `orchestrator.py` -- DAG scheduling, parallel execution, event streaming
- Ontology hard-enforcement on all predictor/barrier/coping paths before persistence

---

## Execution

```bash
# Single cycle
python evaluation/integrated_pipeline/run_pipeline.py --mode synthetic_v1

# Multi-cycle
python evaluation/integrated_pipeline/run_pipeline.py --mode synthetic_v1 --cycles N

# Frontend
python src/frontend/app.py
```

> Do not invoke individual stage scripts directly -- the pipeline script ensures artifact path consistency across cycles.
