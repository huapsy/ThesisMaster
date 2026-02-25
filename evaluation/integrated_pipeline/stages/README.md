# PHOENIX Integrated Stage Registry

This folder defines the sequential PHOENIX stage map used by the integrated pipeline launcher.

## Core Engine Sequence

1. `00 Pseudoprofile Generation` (`pseudodata`)
2. `01 Readiness Check` (`readiness`)
3. `02 Network Time-Series Analysis` (`network`)
4. `03 Momentary Impact Quantification` (`impact`)
5. `04 Treatment Target Identification` (derived from `handoff` outputs)
6. `05 Updated Observation Model` (derived from `handoff` outputs)
7. `06 Digital Intervention Translation` (`intervention`)
8. `07 Treatment Translation Communication` (`translation_communication`)
9. `08 Iterative Model Update (Next Cycle Input)` (`iterative_update`)

## Quality + Research Sequence (Outside Core Engine)

- `S1 Impact Visualization (Support)` (`visualization`)
- `S2 Research Reporting (Support)` (`reporting`)

## Files

- `flow_registry.py`: canonical flow metadata and dependency graph for summary serialization.
- `07_generate_treatment_translation_summary.py`: end-stage communication summary generator from Step-03/04/05 artifacts.

The integrated pipeline imports this stage registry so pipeline summaries and UI labels stay aligned with PHOENIX flow semantics.
