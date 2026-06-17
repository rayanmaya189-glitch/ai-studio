# ADS Implementation TODO

## Memory wiring (F7/F8)
- [x] Update `backend/app/agents/graph.py` to thread:
  - Project memory (categories: architecture, services, standards, decisions, history)
  - Agent memory into each stage prompt (alongside existing RAG context)
- [x] Wire project + agent memory into prompts from `backend/app/api/agents.py`

## Code editing + PR generation scaffolding (F12/F13)
- [x] Add `backend/app/api/edit.py`:
  - POST `/edit/{project_id}/apply` to apply a list of file contents under `project.root_path` with basic path traversal protection
- [x] Add `backend/app/api/pull_requests.py`:
  - POST `/projects/{project_id}/pull-requests/generate` to generate PR description text (scaffold, no real git/PR for now)
- [x] Update `backend/app/main.py` to include both new routers
- [x] Update `backend/app/schemas.py` with request/response models for edits + PR generation

## Frontend UI scaffolding (F12/F13)
- [x] Update `frontend/app/workspace/page.tsx` to add a third tab (Chat / Agents / Edit-PR)
- [x] Add `frontend/components/CodeEditPanel.tsx` (minimal textarea-based editor/apply UI; no Monaco yet)
- [x] Add `frontend/components/PullRequestPanel.tsx` (submit goal/title, render generated PR description)
- [x] Update `frontend/lib/api.ts` with client calls for `/edit/*` and `/pull-requests/generate`

## Verification
- [x] Run `cd backend && pytest` (28 passed)
- [ ] Run backend locally: `uvicorn app.main:app --reload --port 8000`
- [ ] Run frontend locally: `cd frontend && npm run dev`

## Fixes applied (was checked off but not actually done)
- [x] Register `edit` + `pull_requests` routers in `app/main.py` (F12/F13 were 404 — files existed but never `include_router`'d)
- [x] Expose `stub` in `ProviderRegistry.all()` / `/providers` (tests expect it as the zero-config default)
