# PHOENIX Frontend (Flask)

Interactive debugging UI for the PHOENIX engine, built to inspect and run the thesis pipeline with high-detail runtime logging.

## What It Covers

- Session-based intake: complaint text + optional person/context.
- Step 01→02 execution:
  - mental-state operationalization,
  - initial observation-model construction,
  - model visualization artifact collection.
- Data collection stage:
  - variable-level collection schema preview,
  - pseudodata synthesis with configurable points/missingness/seed,
  - manual CSV upload fallback.
- Iterative PHOENIX cycle trigger:
  - cycle starts from current session pseudodata + model artifacts (Step 01/02 handled in Model Creation),
  - core engine flow: readiness -> network -> impact -> Step-03/04 -> Step-05 -> treatment communication,
  - quality-and-research flow: impact visualization + research reporting,
  - run summaries with explicit `engine_stage_flow` and `quality_and_research_flow`.
  - communication component appears only after final cycle communication is generated (not pre-shown at intake).
  - startup LLM health-check/fallback state is surfaced in runtime component status text.
- Comprehension dashboard:
  - interactive time-series chart sourced from session CSV (no manual PNG upload required),
  - impact/barrier/coping charts plus step-level summaries.
- Full cohort execution:
  - one-click 10-patient (or custom N) end-to-end runs,
  - bounded patient-level parallelism,
  - persisted cohort manifests with per-patient artifact pointers.
- Realtime streaming logs via SSE for every background job.
  - stream endpoint emits keepalive heartbeats and supports cursor resume (`after=<log_index>`) for reconnect-safe long runs.

## Directory Layout

```text
frontend/
├── app.py
├── phoenix_frontend/
│   ├── config.py
│   ├── routes/
│   │   ├── ui.py
│   │   └── api.py
│   ├── services/
│   │   ├── cohort.py
│   │   ├── job_manager.py
│   │   ├── phoenix_service.py
│   │   ├── pseudodata.py
│   │   └── session_store.py
│   ├── static/
│   └── templates/
└── workspace/
    ├── cohort_runs/ (cohort manifests and batch-level metadata)
    └── sessions/    (runtime artifacts, per session)
```

## Run

```bash
python frontend/app.py
```

Or launch through the integrated pipeline launcher:

```bash
python evaluation/integrated_pipeline/run_pipeline.py --ui
```

Open:

- [http://127.0.0.1:5050](http://127.0.0.1:5050)

## Environment Notes

- `OPENROUTER_API_KEY` is the primary key for LLM-enabled runs.
- Frontend app startup auto-loads repo `.env` when present.
- Frontend subprocesses mirror `OPENROUTER_API_KEY` into `OPENAI_API_KEY` and enforce `OPENAI_BASE_URL=https://openrouter.ai/api/v1` for legacy scripts.
- `OPENAI_API_KEY` remains an optional fallback.
- LLM execution is enabled by default in the UI; each run form includes a `Disable LLM` toggle.
- LLM model fields support live catalog lookup from OpenRouter (`/api/llm/models`) with type-ahead suggestions.
- Optional overrides:
  - `PHOENIX_REPO_ROOT`
  - `PHOENIX_FRONTEND_WORKSPACE`
  - `PHOENIX_PYTHON_EXE`
  - `PHOENIX_DISABLE_LLM` (`true/false`, enforced globally in UI)

## Runtime Data Safety

- Frontend writes only under `frontend/workspace/` (`sessions/` + `cohort_runs/`).
- No ontology structure/content is modified.
- Session files are isolated and can be inspected independently for reproducibility.
