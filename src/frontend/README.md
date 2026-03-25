# PHOENIX Frontend (Flask)

Research-focused dashboard for the PHOENIX engine with a wizard-style pipeline interface, interactive Chart.js visualizations, and real-time SSE log streaming.

## Features

### Wizard-Style Pipeline Interface
The frontend guides users through 5 sequential pipeline steps, each as a focused panel:

| Step | Phase | Controls |
|---|---|---|
| 01 | **Intake** | Complaint text, person context, environment context |
| 02 | **Model Construction** | LLM model selector, ontology constraints, critic configuration |
| 03 | **Data Collection** | Pseudodata synthesis (time points, missing rate, seed) or manual CSV upload |
| 04 | **Analysis Cycle** | HUA sub-stages with compact progress tracker |
| 05 | **Intervention** | HAPA-based intervention plan with barrier-coping pairs |

### Dashboard Tab
- KPI cards: readiness score, analysis tier, top predictor, barrier count
- Chart.js visualizations: impact predictors, network dynamics (animated canvas), time-series, readiness components, barrier distribution, coping strategies
- Stage analytics: readiness/network/impact/runtime overviews
- Treatment communication summary

### Logs Tab
- Component status grid (17 runtime components)
- Live process summary with recent events
- Realtime log console with SSE streaming and verbosity control (concise/balanced/detailed)

### One-Click Pipeline Execution
- Full pipeline run with multi-cycle support (configurable cycles, memory window)
- Cohort batch execution (N patients in parallel)
- Advanced configuration: prompt budget, critic thresholds, network parameters

## Architecture

```text
src/frontend/
├── app.py                           # Flask entry point (port 5050)
└── phoenix_frontend/
    ├── __init__.py                   # App factory
    ├── config.py                    # Path configuration
    ├── routes/
    │   ├── ui.py                    # 3 UI routes (index, session create, session detail)
    │   └── api.py                   # 14 REST API routes
    ├── services/
    │   ├── phoenix_service.py       # Pipeline orchestration (subprocess calls to backend)
    │   ├── session_store.py         # Session persistence (JSON files)
    │   ├── job_manager.py           # Background job execution (threading)
    │   ├── cohort.py                # Multi-patient batch management
    │   ├── pseudodata.py            # Synthetic EMA data generation
    │   ├── communication_agent.py   # LLM-based treatment summaries
    │   └── models.py                # Data classes
    ├── static/
    │   ├── css/app.css              # Design system (dark theme, Inter + JetBrains Mono)
    │   └── js/session.js            # Client-side logic (state, charts, SSE, wizard)
    └── templates/
        ├── base.html                # App shell (sidebar, topbar, content)
        ├── index.html               # Sessions list + new session form
        └── session.html             # Pipeline wizard + dashboard + logs
```

## API Endpoints

| Method | Route | Purpose |
|---|---|---|
| POST | `/api/sessions` | Create session |
| GET | `/api/sessions/<id>/snapshot` | Get session state |
| PATCH | `/api/sessions/<id>/intake` | Update intake |
| POST | `/api/sessions/<id>/jobs/initial-model` | Run Steps 01-02 |
| POST | `/api/sessions/<id>/jobs/synthesize` | Synthesize pseudodata |
| POST | `/api/sessions/<id>/jobs/manual-data` | Upload CSV |
| POST | `/api/sessions/<id>/jobs/run-cycle` | Run analysis cycle |
| POST | `/api/sessions/<id>/jobs/run-full` | Full end-to-end |
| POST | `/api/sessions/<id>/jobs/full-cohort` | Batch cohort |
| GET | `/api/jobs/<id>` | Job status |
| GET | `/api/jobs/<id>/logs` | Job logs |
| GET | `/api/jobs/<id>/stream` | SSE log stream |
| GET | `/api/sessions/<id>/files/<path>` | Serve session files |
| GET | `/api/llm/models` | LLM model catalog |

## Run

```bash
python src/frontend/app.py
# or
python evaluation/integrated_pipeline/run_pipeline.py --ui
```

Open [http://127.0.0.1:5050](http://127.0.0.1:5050).

## Environment

- `OPENROUTER_API_KEY`: primary LLM key (mirrored to `OPENAI_API_KEY` at runtime)
- `PHOENIX_DISABLE_LLM`: set to `true` for deterministic fallback mode
- `PHOENIX_REPO_ROOT`, `PHOENIX_FRONTEND_WORKSPACE`, `PHOENIX_PYTHON_EXE`: optional overrides
- Frontend writes only under `workspace/` (sessions + cohort_runs). No ontology content is modified.
