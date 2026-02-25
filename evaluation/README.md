# Evaluation Workspace

Canonical execution and validation workspace for the PHOENIX engine.

## Directory Map

- `integrated_pipeline/`: end-to-end runner (`run_pipeline.py`, `run_engine_pipeline.py`) and stage wiring.
- `sequential/`: manually runnable stage modules (`run_step.py` per stage).
- `quality_and_research/quality_assurance/`: pytest suites + contract validation.
- `quality_and_research/research_communication/`: research report generation utilities.
- `integrated_pipeline/runs/`: run-scoped engine outputs and iterative cycle artifacts.
- `artifacts/`: migrated legacy outputs retained for traceability.

## PHOENIX Core Engine Flow (Canonical)

1. `00` pseudoprofile generation / ingestion (free-text source)
2. `01` operationalization
3. `02` initial observation model
4. `03` readiness check
5. `04` network time-series analysis
6. `05` momentary impact quantification
7. `06` target identification + updated observation model (Step-03 + Step-04)
8. `07` HAPA digital intervention (Step-05)
9. `08` treatment translation communication
10. iterative update packaging for next cycle input

## Quality + Research Flow (Support, Not Core Engine)

1. `09` impact visualization export
2. `10` research report generation
3. QA/CI validation suites

## Standard Run Output Layout

`evaluation/integrated_pipeline/runs/<run_id>/`

- `00_operationalization/`
- `01_initial_observation_model/`
- `02_pseudodata_generation/`
- `03_readiness_check/`
- `04_time_series_analysis/network/`
- `05_momentary_impact_coefficients/`
- `06_target_identification_and_model_update/`
- `07_hapa_digital_intervention/`
- `08_treatment_translation_communication/`
- `09_impact_visualizations/` (support)
- `10_research_reports/` (support)
- `logs/`
- `pipeline_summary.json`
- `cycles/cycle_<NN>/` (same stage layout; cycle 2+ typically skips `00/01` via iterative start-from-pseudodata, with explicit skip manifests)
