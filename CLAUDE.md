# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## What is being built

**AI Development Studio (ADS)** — a self-hosted platform where AI agents work on large microservice codebases (50+ services, 500k+ LOC). The full product spec is in `docs/requirement.md`; read it before making architectural decisions. The PRD frames it as **local-first** (Ollama models, local storage). This scaffold widens that to a pluggable provider layer (Ollama is one of several backends) while keeping the zero-cloud-dependency option intact.

User flow: pick a project folder → scan it → build a project-specific knowledge base (RAG + code graph) → work in a chat-driven workspace where specialized agents collaborate.

## Project state: scaffold, not greenfield

Every subsystem is wired end-to-end behind real interfaces. The **scanner and code graph are real** (Tree-sitter parsing, heuristic service/endpoint/DB detection). What is still **stubbed** is the multi-agent orchestration: `backend/app/agents/graph.py` is a single-agent passthrough, not the LangGraph Planner→Architect→Coding→Review→Testing chain the PRD describes. Memory CRUD (`app/memory/store.py`) is real but not yet threaded into agent prompts.

## Commands

From `ai-studio/`, `make help` lists shortcuts. Underlying commands:

```bash
# Backing services (OPTIONAL — see zero-config note below)
docker compose up -d postgres qdrant          # core stack
docker compose --profile graph up -d           # + Neo4j (optional)

# Backend (Python ≥3.12)
cd backend && python3 -m venv .venv && . .venv/bin/activate && pip install -r requirements.txt
uvicorn app.main:app --reload --port 8000      # health: /health, docs: /docs

# Frontend
cd frontend && npm install && npm run dev       # http://localhost:3000

# Tests / lint (backend)
cd backend && pytest                            # full suite
cd backend && pytest tests/test_scanner.py      # single file
cd backend && pytest tests/test_scanner.py::test_name   # single test
cd backend && ruff format app tests && ruff check --fix app tests
```

The frontend has no test suite; `npm run lint` runs `next lint`.

## Architecture: the zero-config invariant

The single most important design decision, enforced across the whole stack: **a fresh clone boots and runs with no external services and no API keys.** Preserve this when adding features — every external dependency must degrade gracefully, never hard-fail. Three fallback layers implement it:

1. **LLM providers** (`app/providers/`): the `stub` provider is always registered and `available()`. Model references everywhere use the form `"<provider>:<model>"` (e.g. `ollama:qwen2.5-coder`, `anthropic:claude-opus-4-8`). `ProviderRegistry.resolve()` returns the configured default, and **falls back to `stub:echo` whenever the requested provider lacks creds or its daemon is down** — so callers never branch on availability. Adding a provider = subclass `LLMProvider` (`chat` + `embed` + `available` + `list_models`) and register it in `registry.py`. OpenAI/OpenRouter/NIM all share `OpenAICompatProvider`.
2. **Vector store** (`app/rag/vector_store.py`): `get_vector_store()` probes Qdrant over HTTP and returns `QdrantStore` if reachable, else `LocalStore` (brute-force cosine over a per-project JSON file). Both implement the same `VectorStore` ABC. The local store is explicitly *not* the 500k-LOC production path — it's the fallback.
3. **Database** (`app/db.py`, `app/config.py`): defaults to SQLite (`./ads.db`); set `DATABASE_URL` to point at Postgres. Schema is created via `Base.metadata.create_all` on startup (`init_db` in the FastAPI lifespan) — **there are no migrations yet**; introduce Alembic before the schema is considered stable.

All config flows through `app/config.py` (`pydantic-settings`, reads `.env`). Every credential is optional. See `.env.example`.

## The scan pipeline (data flow that spans files)

`POST /scan/{project_id}` (`app/api/scan.py`) is the orchestration spine — understanding it explains how most subsystems connect:

1. **Scanner** (`app/scanner/scanner.py`) walks the folder, uses `tree_sitter_language_pack.process()` to parse symbols + imports across the 7 PRD languages, and applies regex heuristics for HTTP endpoints, database engines, and services (a dir is a "service" if it has a build marker like `package.json`/`go.mod`/`Dockerfile`). Returns a `ScanMetadata` dataclass. Hard caps (`_MAX_FILE_RECORDS`, `_MAX_PARSE_BYTES`, `max_files`) keep it within the PRD's <5 min/100k-files budget.
2. The API persists `File` + `Service` rows (bounded by `_MAX_FILE_INSERTS`), then calls **`build_code_graph`** (`app/graph/code_graph.py`), which builds service/database nodes and infers service→service edges from cross-service import strings, persisting them to the `code_graph` table.
3. Then **`ingest_project`** (`app/rag/ingest.py`) chunks embeddable files, embeds them via the provider layer, and upserts into the vector store. **This step is best-effort** — a RAG failure is caught and recorded in metadata, never fails the scan.

`app/scanner/languages.py` owns extension→language and the `IGNORE_DIRS` set, shared by scanner and RAG ingester. Keep RAG (semantic retrieval) and the code graph (structural service topology) conceptually separate — they answer different questions.

Chat (`app/api/chat.py`) closes the loop: it retrieves RAG context for the project, passes it to `run_chat`, and persists both turns as `Conversation` rows.

## Backend layout

- `app/main.py` — FastAPI app, CORS, router registration, `init_db` on lifespan.
- `app/models.py` — the 10 PRD tables (Project, Service, File, Agent, Task, AgentMemory, ProjectMemory, Embedding, CodeGraphNode, Conversation). IDs are 32-char uuid hex; loosely-structured data lives in JSON columns. The `Embedding` row is a *pointer* — the actual vector lives in the vector store.
- `app/schemas.py` — Pydantic request/response models (the API contract the frontend's `lib/api.ts` mirrors).
- `app/api/` — one router per feature area; docstrings tag the PRD feature codes (F2 scan, F3 RAG, F4 graph, F5/F6 agents, F8 memory, F10 chat).
- The 7 agent roles (planner, architect, coding, review, testing, documentation, ocr) are seeded lazily on first `GET /agents` with `stub:echo` defaults; each role's model is independently reassignable (`PUT /agents/{id}/model`). **Model-per-agent is a core PRD requirement, not a config nicety.**

## Two memory systems (keep them separate)

- **Agent Memory** (`agent_memory`) — per-agent: past tasks, fixes, learned style.
- **Project Memory** (`project_memory`) — per-project, categorized by the PRD's folder taxonomy (`architecture`, `services`, `standards`, `decisions`, `history`), enforced in `app/memory/store.py`. Persists across sessions.

## Frontend

Next.js 15 (App Router) + React 19 + Tailwind + React Flow. `next.config.mjs` rewrites `/api/*` → the FastAPI backend (`BACKEND_URL`, default `localhost:8000`), so the browser uses same-origin paths. **All backend calls go through the typed client in `lib/api.ts`** — extend it rather than calling `fetch` directly from components. Pages: `app/page.tsx` (project picker), `app/dashboard/` (React Flow service graph), `app/workspace/` (chat). Monaco editor is planned per the PRD but not yet wired.

## Non-functional targets to design against

Project scan < 5 min for 100k files; vector search < 500ms; agent response < 10s; must scale to millions of vectors. Choices that work at toy scale but not at 500k LOC are out of spec — this is why the Qdrant/Postgres paths exist alongside the zero-config fallbacks.
