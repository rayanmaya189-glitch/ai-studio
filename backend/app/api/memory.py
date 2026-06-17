"""F7/F8 - Agent memory and project memory over HTTP.

Thin CRUD endpoints over the helpers in ``app/memory/store.py``. These let the
UI populate the two memory systems that the autonomous pipeline already reads
from (``run_agent_pipeline`` threads project memory and per-agent memory into
each stage's prompt).

Two memory systems, kept separate (see CLAUDE.md):
- agent memory  — per-agent notes (past tasks, fixes, learned style)
- project memory — per-project, categorized by the PRD folder taxonomy
"""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.db import get_db
from app.memory.store import (
    PROJECT_MEMORY_CATEGORIES,
    add_agent_memory,
    add_project_memory,
    get_agent_memory,
    get_project_memory,
)
from app.models import Agent, Project
from app.schemas import (
    AgentMemoryCreate,
    AgentMemoryOut,
    ProjectMemoryCreate,
    ProjectMemoryOut,
)

router = APIRouter(tags=["memory"])


# ---- Agent memory (F7) ----
@router.get("/agents/{agent_id}/memory", response_model=list[AgentMemoryOut])
def list_agent_memory(agent_id: str, db: Session = Depends(get_db)) -> list:
    if db.get(Agent, agent_id) is None:
        raise HTTPException(status_code=404, detail="Agent not found")
    return get_agent_memory(db, agent_id)


@router.post("/agents/{agent_id}/memory", response_model=AgentMemoryOut)
def create_agent_memory(agent_id: str, payload: AgentMemoryCreate, db: Session = Depends(get_db)):
    if db.get(Agent, agent_id) is None:
        raise HTTPException(status_code=404, detail="Agent not found")
    return add_agent_memory(
        db,
        agent_id=agent_id,
        content=payload.content,
        kind=payload.kind,
        project_id=payload.project_id,
    )


# ---- Project memory (F8) ----
@router.get("/projects/{project_id}/memory", response_model=list[ProjectMemoryOut], tags=["memory"])
def list_project_memory(project_id: str, db: Session = Depends(get_db)) -> list:
    if db.get(Project, project_id) is None:
        raise HTTPException(status_code=404, detail="Project not found")
    return get_project_memory(db, project_id)


@router.post("/projects/{project_id}/memory", response_model=ProjectMemoryOut, tags=["memory"])
def create_project_memory(
    project_id: str, payload: ProjectMemoryCreate, db: Session = Depends(get_db)
):
    if db.get(Project, project_id) is None:
        raise HTTPException(status_code=404, detail="Project not found")
    try:
        return add_project_memory(
            db,
            project_id=project_id,
            category=payload.category,
            title=payload.title,
            content=payload.content,
        )
    except ValueError as exc:
        # Unknown category — surface the valid set to the caller.
        raise HTTPException(
            status_code=400,
            detail=f"{exc}. Valid categories: {', '.join(PROJECT_MEMORY_CATEGORIES)}",
        ) from exc
