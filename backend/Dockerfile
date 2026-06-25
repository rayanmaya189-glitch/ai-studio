# AI Development Studio — backend (FastAPI).
FROM python:3.12-slim AS base

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_NO_CACHE_DIR=1 \
    LOG_FORMAT=json

WORKDIR /app

# git is needed at runtime for the PR generator (real branch/commit/diff).
RUN apt-get update \
    && apt-get install -y --no-install-recommends git curl \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt ./
RUN pip install -r requirements.txt

COPY . .

# Run as non-root.
RUN useradd --create-home --uid 10001 appuser \
    && chown -R appuser:appuser /app
USER appuser

EXPOSE 8754

HEALTHCHECK --interval=30s --timeout=5s --start-period=20s --retries=3 \
    CMD curl -fsS http://localhost:8754/health || exit 1

# Apply migrations (best-effort), then serve. create_all still covers SQLite.
CMD ["sh", "-c", "alembic upgrade head || true; uvicorn app.main:app --host 0.0.0.0 --port 8754"]
