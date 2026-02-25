# Agentic Framework · PHOENIX Engine

Contains the five LLM-mediated agent stages that form the core of the PHOENIX Multi-Agent System. Each stage pairs a **generative agent** with a **critic agent** in an iterative PASS / REVISE loop governed by `guardrail.py`.

## Agent Stages

### Stage 01 · Complaint Decomposer Agent (`01_OperationalizationMentalHealthProblem/`)
- **Input**: raw clinical intake text / EMA self-report data
- **Output**: structured criterion set (DSM/ICD-aligned, JSON)
- **Role**: free-text → operationalised problem specification

### Stage 02 · Observation Model Creator + Critic (`02_ConstructionInitialObservationModel/`)
- **Creator Agent** (`step02_initial_model_system.md`): builds the initial criterion-predictor network; encodes predictor–criterion edges with `relevance_score_0_1`
- **Critic Agent** (`step02_initial_model_critic_system.md`): composite score → **PASS** (proceed) or **REVISE** (retry with feedback)
- Structural validity enforced via PHOENIX ontology leaf-path matching

### Stage 03 · Treatment Target Identifier + Critic (`03_TreatmentTargetIdentification/`)
- **Input**: approved initial model + BFS-ranked candidate predictor paths
- **Identifier Agent** (`step03_target_selection_system.md`): integrates evidence; selects high-impact targets
- **Critic Agent** (`step03_target_selection_critic_system.md`): safety and domain-boundary validation
- Back-edge: if Stage 04 updates the model, Stage 03 can re-target

### Stage 04 · Updated Observation Model Creator + Critic (`04_ConstructionUpdatedObservationModel/`)
- **Creator Agent** (`step04_observation_update_system.md`): `fuse_updated_model_matrix` — adaptively weights nomothetic (population) vs. idiographic (individual) evidence:
  - `idiographic_weight = clamp(0.30 + 0.50 · readiness_0_1)`
  - `nomothetic_weight  = 1 − idiographic_weight`
- **Critic Agent** (`step04_observation_update_critic_system.md`): lineage consistency + history-append validation
- Reads `impact_matrix.csv` from HUA Impact Quantifier Agent

### Stage 05 · Digital Intervention Mapper + Critic (`05_TranslationDigitalIntervention/`)
- **Mapper Agent** (`step05_hapa_intervention_system.md`): synthesises HAPA-based EMA protocol; ranks barriers and coping strategies
- **Critic Agent** (`step05_hapa_intervention_critic_system.md`): clinical safety guardrail + HAPA coherence check
- **Output**: `intervention_plan.json` — actionable digital prescription

---

## Shared Infrastructure

| Module | Role |
|---|---|
| `utils/agentic_core/shared/llm_runtime.py` | LLM execution with retry, repair, fallback |
| `utils/agentic_core/shared/guardrail.py` | `decision_from_score()` → PASS / REVISE |
| `utils/agentic_core/shared/target_refinement.py` | BFS candidate scoring + fuse_updated_model_matrix |
| `utils/agentic_core/shared/feasibility.py` | Predictor feasibility matching (suitability × utility-risk) |
| `utils/agentic_core/shared/contracts/` | JSON schema validators for every stage output |
| `utils/agentic_core/prompts/` | Centralised prompt registry (`prompts_manifest.json`) |

---

## Entry Point

```bash
python evaluation/integrated_pipeline/run_pipeline.py --mode synthetic_v1
```

See [`src/README.md`](../README.md) for the full multi-agent architecture diagram and cycle logic.
