# 🐦‍🔥 PHOENIX Engine 🐦‍🔥

The PHOENIX engine conceptualises mental health support as a closed-loop workflow that iteratively optimizes the intervention proposal based on data from previous cycles.

(**P**ersonalized **H**ierarchical **O**ptimization **E**ngine for **N**avigating **I**nsightful e**X**plorations)

## 🏛️ Academic Context
This research-grade software is being created for a Ghent University **master's thesis** that aims to enhance the clinical translation abilities of longitudinal **mental health applications**: toward an adaptive approach for **idiographic modelling** by using **ontologies and large language models**.

| **Field** | **Value** |
|---|---|
| **Institution** | Ghent University |
| **Author** | Stijn Van Severen |
| **Supervisors** | Geert Crombez, Annick De Paepe |

## 🧭 PHOENIX Scope

PHOENIX separates two concerns:

- **Core engine flow**: clinical/analytic decision flow from intake to iterative model carry-over.
- **Research support flow**: visualization, QA, and research reporting for validation and communication.

This separation keeps scientific validation transparent without mixing support tasks into core decision logic.

## 🔁 End-to-End Stage Map

PHOENIX is a modular, multi-agent system that starts from free-text complaints, builds an initial observation model, analyzes time-series dynamics, proposes targets/interventions, and packages iterative updates for the next cycle.

![PHOENIX engine — Multi Agent System Architecture](src/overview/create_flowchart.png)

## 🐦‍🔥 PHOENIX Ontology with LLM-based Mappings
The following ontology was developed to support the PHOENIX engine's reasoning and decision-making processes. It includes a comprehensive set of concepts and relationships relevant to mental health interventions, such as mental health symptoms and treatment options. 

![PHOENIX_ontology.png](src%2Foverview%2FPHOENIX_ontology.png)

## 🚀 Quick Setup of PHOENIX engine

### 1. Clone repository

```bash
git clone https://github.com/stvsever/ThesisMaster.git
cd MASTERPROEF
```

### 2. Create Python environment (3.11+)

```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
pip install -r requirements.txt
```

### 3. Configure `.env` for LLM-enabled runs

Create or update `.env` in repository root:

```bash
OPENROUTER_API_KEY=<your_openrouter_key>
OPENAI_BASE_URL=https://openrouter.ai/api/v1
```

Runtime behavior:
- `OPENROUTER_API_KEY` is primary.
- Runtime mirrors it to `OPENAI_API_KEY` for backward-compatible scripts.
- Default model is `gpt-5-nano` (resolved as `openai/gpt-5-nano` when routed via OpenRouter).

### 4. Optional smoke validation

If you want to quickly validate the integrated pipeline on a single profile with minimal iterations, you can run the smoke test:

```bash
make pipeline-smoke
```

## 🗂️ Repository Structure

A client-side knowledge graph creator (GitNexus) was used to generate  a comprehensive knowledge graph of the entire codebase architecture and component interactions is provided below:

<div align="center">
  <img src="src/overview/gitnexus_overview.png" alt="PHOENIX GitNexus Codebase Graph" width="800" />
</div>

The main codebase is organized into three primary directories: `src/` for core engine logic, `evaluation/` for all evaluation scripts and research support, and `frontend/` for the Flask application. The structure is designed to maintain a clear separation of concerns while facilitating modular development and testing.

```text
MASTERPROEF/
├── src/                            # Core engine logic and ontology-backed components
│   ├── SystemComponents/              # Agentic framework, HUA, intervention components
│   ├── utils/                         # Shared agentic runtime, mappings, feasibility utilities
│   └── overview/                      # Architecture visuals
├── evaluation/                     # Sequential scripts + integrated pipeline + QA/research
│   ├── sequential/                    # Stage-wise run_step.py scripts (00..08)
│   ├── integrated_pipeline/           # run_pipeline.py and run_engine_pipeline.py
│   └── quality_and_research/          # pytest suites, schema contracts, research reporting
├── frontend/                       # Flask app, UI routes, runtime workspace integration
├── .github/                        # CI/CD workflows
├── pyproject.toml                  # Python package metadata and constraints
├── requirements.txt                # Dependency baseline
└── README.md                       # Root documentation
```

## 💻 Run PHOENIX from CLI

### A. Standard integrated run

The following command executes the full PHOENIX pipeline with default settings, processing the synthetic_v1 dataset through all stages and generating comprehensive outputs:
```bash
python evaluation/integrated_pipeline/run_pipeline.py --mode synthetic_v1
```

### B. Single profile selection

The following command runs the pipeline on the `synthetic_v1` dataset but limits the execution to a single profile matching the pattern `pseudoprofile_FTC_ID001`. This allows for focused testing and debugging on a specific case:
```bash
python evaluation/integrated_pipeline/run_pipeline.py --mode synthetic_v1 \
  --pattern pseudoprofile_FTC_ID001 \
  --max-profiles 1
```

### C. Iterative run (2 cycles)

The following command executes the PHOENIX pipeline for 2 complete cycles, allowing you to observe how the system iteratively refines its outputs based on previous cycle data. The `--profile-memory-window 3` flag enables the system to retain information from the last 3 profiles for informed decision-making in subsequent cycles:

```bash
python evaluation/integrated_pipeline/run_pipeline.py --mode synthetic_v1 \
  --cycles 2 \
  --profile-memory-window 3
```

Runtime note:
- If a cycle is `readiness_aligned` and only contemporaneous correlation analysis is feasible, PHOENIX now applies a correlation-baseline impact fallback so downstream Step-03/04/05 and communication stages still execute and persist outputs.
- If Step-02 model generation fails (for example provider/network failure), PHOENIX now builds complaint-grounded fallback Step-02 artifacts directly from Step-01 operationalization output, instead of copying unrelated historical profile artifacts.
- For iterative cycles started via `--start-from-pseudodata`, PHOENIX now resolves `initial_model_runs_root` from the active run lineage (same run id) so Step-03/04 stay anchored to the current cycle history.

## 🖥️ Run PHOENIX from Frontend

Use the following command to start the Flask frontend:

```bash
python frontend/app.py
# or
python evaluation/integrated_pipeline/run_pipeline.py --ui
```

Open [http://127.0.0.1:5050](http://127.0.0.1:5050).

Frontend provides:
- Intake for complaint/person/environment context
- Live component status and streaming logs
- One-click full end-to-end run from free-text complaint (with iterative cycle controls)
- Step-level run controls and advanced configuration toggles
- Iterative-cycle execution and output inspection

## 📦 Outputs and Validation Targets

Integrated outputs are saved under:

```text
evaluation/integrated_pipeline/runs/<run_id>/
```

Key artifacts to inspect:
- `00_operationalization/` through `10_research_reports/`
- `pipeline_summary.json`
- `llm_startup_health_check.json`
- Stage logs (`stage.log`, `stage_events.jsonl`, `stage_trace.json`)
- Profile-specific JSON/CSV outputs per step
- Profile-specific human-readable summaries:
  - `07_hapa_digital_intervention/<profile_id>/step05_hapa_intervention.md`
  - `08_treatment_translation_communication/<profile_id>/treatment_translation_communication.md`

## ✅ Quality Assurance and CI/CD

Run locally:

```bash
make qa-unit
make qa-integration
make qa-smoke
make qa-all
```

Automated workflows:
- `.github/workflows/ci.yml`
- `.github/workflows/smoke_pipeline.yml`

Schema/contract validation entrypoint:
- `evaluation/quality_and_research/quality_assurance/validate_contract_schemas.py`

## 📜️ License

This project is licensed under **GNU General Public License v3.0**. See [`LICENSE`](./LICENSE).

What this means in practice:
- You may **use, study, modify, and redistribute** this code.
- If you distribute modified versions (or software that includes GPL-covered parts), you must:
  - keep it under GPL-compatible terms,
  - provide corresponding source code,
  - preserve copyright and license notices,
  - document meaningful changes.
- The software is provided **without warranty**.

For academic reuse, cite the thesis context appropriately and keep provenance of methodological changes explicit.

> [!CAUTION]
> **EU MDR / PRE-CLINICAL DISCLAIMER**
> PHOENIX is a **Clinical Decision Support System (CDSS) prototype** designed for research purposes. It is **NOT** a certified medical device under the EU Medical Device Regulation (MDR 2017/745) or FDA guidelines. Do not use for primary diagnostic decisions. All outputs must be verified by a qualified clinician.
