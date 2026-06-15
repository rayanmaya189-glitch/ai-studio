# AI Development Studio (ADS)

A self-hosted platform where local/cloud AI agents work on large microservice
codebases. See [`docs/requirement.md`](docs/requirement.md) for the full PRD and
[`CLAUDE.md`](CLAUDE.md) for architecture notes.

> **Status:** scaffold. Every service is wired end-to-end; feature logic
> (scanner, RAG, code graph, multi-agent flows) is stubbed behind real
> interfaces. The app runs with **zero configuration** thanks to a built-in
> `stub` LLM provider and a default SQLite database.

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
uvicorn app.main:app --reload --port 8000
```
- Health check: http://localhost:8000/health
- Interactive API docs: http://localhost:8000/docs

### 3. Frontend
```bash
cd frontend
npm install
npm run dev          # http://localhost:3000
```

## LLM providers

Configure providers in `.env`. The default model is `stub:echo` so nothing is
required. Set any of `OPENAI_API_KEY`, `OPENROUTER_API_KEY`, `NIM_API_KEY`,
`ANTHROPIC_API_KEY`, or run Ollama locally, then point `DEFAULT_CHAT_MODEL` at
`<provider>:<model>` (e.g. `anthropic:claude-opus-4-8`, `ollama:qwen2.5-coder`).

## Tests
```bash
cd backend && pytest
```

## Make shortcuts
`make help` lists `up`, `down`, `install-backend`, `install-frontend`,
`backend`, `frontend`, `test`, `fmt`.
