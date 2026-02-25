# Research Communication

Utilities for generating publication-ready summaries from integrated PHOENIX runs.

## Script

- `generate_pipeline_research_report.py`

## Inputs and Outputs

Input: `evaluation/integrated_pipeline/runs/<run_id>/`

Outputs:
- `run_report.md`
- `run_report.json`
- `component_status.csv`
- `profile_overview.csv`

## Example

```bash
python evaluation/quality_and_research/research_communication/generate_pipeline_research_report.py \
  --run-root "evaluation/integrated_pipeline/runs/<run_id>" \
  --output-root "evaluation/integrated_pipeline/runs/<run_id>/05_research_reports"
```

## Scope

Current reports cover synthetic-data runs, with schema compatibility for future real-world ingestion workflows.
