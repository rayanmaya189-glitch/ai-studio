# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project state

This is a **greenfield project**. As of now the repository contains only the product requirements document (`docs/requirement.md`) — no source code, build system, dependencies, tests, or git history exist yet. The full spec lives in `docs/requirement.md`; read it before making architectural decisions.

There are no build/lint/test commands yet. When scaffolding the project, establish these per the stack below and document them here.

## What is being built

**AI Development Studio (ADS)** — a self-hosted platform where local AI agents work on large microservice codebases (50+ services, 500k+ LOC). It is **local-first by hard requirement**: no cloud dependency, models run via Ollama, storage is local. Honor this constraint in every design choice.

The user-facing flow is: pick a project folder → scan it → build a project-specific knowledge base (RAG + code graph) → work in a chat-driven workspace where specialized agents collaborate, optionally fully autonomously.

## Intended architecture (from the PRD)

The system is a pipeline, not a monolith. Understanding how the stages feed each other matters more than any single component:

1. **Project Scanner** (Tree-sitter) parses an arbitrary project folder across 7 languages (Python, Java, Go, TS/JS, C#, Rust) and emits structured metadata: services, APIs, databases, infra.
2. **RAG system** embeds code + docs + specs + infra files (default embedding model `nomic-embed-text`) into a vector DB (default **Qdrant**, alternatives Chroma/Weaviate). Powers retrieval for agents.
3. **Code Graph Engine** maps relationships (service→service, class, function, API, event flows), optionally backed by **Neo4j**. Distinct from RAG: graph is for structural reasoning, vectors for semantic retrieval.
4. **Multi-agent system** (LangGraph) orchestrates 7 specialized agent roles — Planner, Architect, Coding, Review, Testing, Documentation, OCR. **Each agent is assigned its own Ollama model** (e.g. Coding→`qwen2.5-coder`, Review→`llama3.1:8b`); model-per-agent is a core requirement, not a config nicety.
5. **Autonomous mode** chains agents Planner → Architect → Coding → Review → Testing to take a single user goal to a complete implementation.

### Stack
- **Frontend**: Next.js + React + Tailwind, Monaco editor (code editing/diffs), React Flow (service dependency dashboard).
- **Backend**: FastAPI + LangGraph (agent orchestration).
- **Storage**: PostgreSQL (relational: projects, agents, tasks, memory, conversations) + Qdrant (vectors). Neo4j optional for the code graph.

### Two memory systems (keep them separate)
- **Agent Memory** — per-agent: past tasks, fixes, learned style preferences.
- **Project Memory** — per-project, file-tree structured (`architecture/`, `services/`, `standards/`, `decisions/`, `history/`): architecture decisions, coding standards, domain knowledge. Persists across sessions.

## Non-functional targets to design against
- Project scan < 5 min for 100k files; vector search < 500ms; agent response < 10s.
- Must scale to millions of vectors. Choices that work at toy scale but not at 500k LOC are out of spec.
