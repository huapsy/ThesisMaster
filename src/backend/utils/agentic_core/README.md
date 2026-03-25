# Agentic Core (`utils/agentic_core`)

Shared runtime infrastructure used by all five PHOENIX agent stages.

## Modules

### `shared/llm_runtime.py`
- Single entry-point for all LLM calls in the engine
- Handles: retry-on-failure, JSON-mode repair, model fallback, token budget enforcement

### `shared/guardrail.py`
- **`decision_from_score(score_0_1, threshold_0_1, critical_issues) → "PASS" | "REVISE"`**
- Used by every critic agent to enforce structured PASS/REVISE decisions
- Composite scoring via `weighted_composite()` across multiple critic dimensions

### `shared/target_refinement.py`
- **BFS Candidate Selector** — scores every PHOENIX ontology leaf path:
  ```
  total = 0.45·mapping + 0.25·HyDE + 0.20·idiographic_anchor + 0.10·domain_bonus
  ```
- **`fuse_updated_model_matrix()`** — computes the updated observation model matrix with the nomothetic/idiographic adaptive weighting
- Path similarity utilities (`path_similarity`, `normalize_path_text`, etc.)

### `shared/feasibility.py`
- Predictor feasibility matching against parent-domain suitability scores
- Aggregates per-predictor `blended_feasibility = 0.75·suitability + 0.25·(1−utility_risk)`

### `shared/contracts/`
- JSON schema contracts for each stage output — validated at every PASS boundary

### `prompts/`
- Centralized prompt registry (`prompts_manifest.json`) with versioned system prompts and user templates for all five stages and their critics

---

See [`src/README.md`](../../README.md) for full system architecture.
