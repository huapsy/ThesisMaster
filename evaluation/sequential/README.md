# PHOENIX Sequential Execution

The sequential flow is organized around numbered stage directories only. Shared helpers and static sequential inputs now live under `evaluation/sequential/utils/`, so the root of this package stays reserved for executable stages plus documentation.

## Core Engine Sequence

1. `00_pseudoprofile_generation/run_step.py`
2. `01_operationalization/run_step.py`
3. `02_initial_observation_model/run_step.py`
4. `03_readiness_check/run_step.py`
5. `04_network_time_series_analysis/run_step.py`
6. `05_momentary_impact_quantification/run_step.py`
7. `06_target_identification_and_model_update/run_step.py`
8. `07_hapa_digital_intervention/run_step.py`
9. `08_treatment_translation_communication/run_step.py`

## Shared Utilities

- `utils/common.py`: shared runner and path helpers for all sequential stages
- `utils/free_text/`: default complaint, person, and context input files used by the step wrappers
- `00_pseudoprofile_generation/utils/`: step-local pseudodata generation and visualization helpers

## Support (Not Core Engine)

- Quality assurance: `evaluation/quality_and_research/quality_assurance/`
- Research communication: `evaluation/quality_and_research/research_communication/`

## Example Commands

```bash
python evaluation/sequential/00_pseudoprofile_generation/run_step.py --help
python evaluation/sequential/01_operationalization/run_step.py --help
python evaluation/sequential/02_initial_observation_model/run_step.py --help
```

## Integrated Pipeline

For full integrated orchestration:

```bash
python evaluation/integrated_pipeline/run_pipeline.py --mode synthetic_v1
```
