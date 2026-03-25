# ─────────────────────────────────────────────────────────────
# 🐦‍🔥 PHOENIX Engine — Docker Image
# Multi-stage build for minimal image size
# ─────────────────────────────────────────────────────────────
FROM python:3.11-slim AS base

# System dependencies for scientific stack (numpy, scipy, matplotlib)
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc g++ gfortran \
    libopenblas-dev liblapack-dev \
    libfreetype6-dev libpng-dev \
    curl \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# ── Dependency layer (cached unless requirements change) ──
COPY requirements.txt .
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir -r requirements.txt

# ── Application layer ──
FROM base AS app

WORKDIR /app
COPY . .

# Create output directory for pipeline runs
RUN mkdir -p /app/evaluation/integrated_pipeline/runs

# Default environment
ENV PYTHONUNBUFFERED=1 \
    PHOENIX_DISABLE_LLM=false \
    FLASK_ENV=production \
    FLASK_APP=src/frontend/app.py

# Expose frontend port
EXPOSE 5050

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=15s --retries=3 \
    CMD curl -f http://localhost:5050/ || exit 1

# Default: run the Flask frontend via gunicorn
CMD ["gunicorn", \
     "--bind", "0.0.0.0:5050", \
     "--workers", "2", \
     "--threads", "4", \
     "--timeout", "300", \
     "src.frontend.app:app"]
