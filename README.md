# AI Development Studio (ADS)

A self-hosted platform where local/cloud AI agents work on large microservice
codebases. See [`docs/requirement.md`](docs/requirement.md) for the full PRD and
[`CLAUDE.md`](CLAUDE.md) for architecture notes.

> **Status:** scaffold, but most subsystems are real — scanner, RAG, code
> graph, and the multi-agent Planner→Architect→Coding→Review→Testing pipeline
> all work end-to-end. Storage runs with **zero configuration** (default SQLite,
> Qdrant→local-file vector fallback), so a fresh clone can scan and browse a
> project immediately. LLM-backed features (chat, the agent pipeline, PR
> generation) require **at least one provider enabled** — configure one in the
> LLM Config page or `.env`; running Ollama locally needs no API key.

## Quick start

### 1. Backing services (optional)
Defaults to SQLite + no vector DB, so this step is optional for a first run.
```bash
docker compose up -d postgres qdrant   # add: --profile graph for Neo4j
```
Then set `DATABASE_URL` / `QDRANT_URL` in `.env` (copy from `.env.example`).

### 2. Backend
```bash
cd backend
python3 -m venv .venv && . .venv/bin/activate
pip install -r requirements.txt
uvicorn app.main:app --reload --port 8754
```
- Health check: http://localhost:8754/health
- Interactive API docs: http://localhost:8754/docs

### 3. Frontend
```bash
cd frontend
npm install
npm run dev          # http://localhost:3000
```

## LLM providers

At least one provider must be enabled before chat/pipeline/PR endpoints work —
the registry registers only providers you enable and `resolve()` raises a clear
error otherwise (no silent stub fallback). Enable one in the LLM Config page, or
configure via `.env`: set any of `OPENAI_API_KEY`, `OPENROUTER_API_KEY`,
`NIM_API_KEY`, `ANTHROPIC_API_KEY`, or run Ollama locally (no key needed), then
point `DEFAULT_CHAT_MODEL` at `<provider>:<model>` (e.g.
`anthropic:claude-opus-4-8`, `ollama:qwen2.5-coder`).

## Tests
```bash
cd backend && pytest
```

## Make shortcuts
`make help` lists `up`, `down`, `install-backend`, `install-frontend`,
`backend`, `frontend`, `test`, `fmt`.
