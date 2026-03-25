# 🐳 PHOENIX Docker

Containerized deployment for the PHOENIX engine.

## Quick Start

```bash
# 1. Clone the repository
git clone https://github.com/stvsever/ThesisMaster.git
cd MASTERPROEF

# 2. Optional: create .env for LLM-enabled runs
cat > .env <<'EOF'
OPENROUTER_API_KEY=<your_openrouter_key>
OPENAI_BASE_URL=https://openrouter.ai/api/v1
EOF

# 3. Start from the repository root
cd docker

# 4. Frontend (web UI on port 5050)
docker compose up --build

# 5. CLI pipeline run (single profile)
docker compose run --rm phoenix-cli --mode synthetic_v1 --max-profiles 1

# CLI with custom arguments
docker compose run --rm phoenix-cli --mode synthetic_v1 --cycles 2 --profile-memory-window 3
```

If you want a deterministic run without live LLM calls, set `PHOENIX_DISABLE_LLM=true` before starting Compose.

## Environment Variables

| Variable | Default | Description |
|---|---|---|
| `OPENROUTER_API_KEY` | *(required for LLM)* | OpenRouter API key |
| `OPENAI_BASE_URL` | `https://openrouter.ai/api/v1` | LLM endpoint |
| `PHOENIX_DISABLE_LLM` | `false` | Set `true` for deterministic mode |
| `PHOENIX_DEFAULT_MODEL` | `gpt-5-nano` | Default LLM model |

## Volumes

Pipeline outputs are persisted to `evaluation/integrated_pipeline/runs/` on the host via Docker volume mount.

## Services

| Service | Description | Port |
|---|---|---|
| `phoenix` | Flask frontend + gunicorn | 5050 |
| `phoenix-cli` | CLI pipeline runner (on-demand) | — |

Activate the CLI profile: `docker compose --profile cli run phoenix-cli [args]`
