"""Agent memory (F7) and project memory (F8) — DB-backed helpers.

These are thin, real CRUD helpers over the AgentMemory / ProjectMemory tables.
They aren't stubbed; what's deferred is *using* them inside agent prompts, which
lands with the LangGraph orchestration in ``agents/graph.py``.
"""

from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import AgentMemory, ProjectMemory

# The project-memory categories mirror the PRD's project-memory/ folder layout.
PROJECT_MEMORY_CATEGORIES = ("architecture", "services", "standards", "decisions", "history")


def add_agent_memory(
    db: Session, agent_id: str, content: str, kind: str = "note", project_id: str | None = None
) -> AgentMemory:
    row = AgentMemory(agent_id=agent_id, content=content, kind=kind, project_id=project_id)
    db.add(row)
    db.commit()
    db.refresh(row)
    return row


def get_agent_memory(db: Session, agent_id: str) -> list[AgentMemory]:
    return list(db.scalars(select(AgentMemory).where(AgentMemory.agent_id == agent_id)))


def add_project_memory(
    db: Session, project_id: str, category: str, title: str, content: str
) -> ProjectMemory:
    if category not in PROJECT_MEMORY_CATEGORIES:
        raise ValueError(f"Unknown project memory category: {category!r}")
    row = ProjectMemory(project_id=project_id, category=category, title=title, content=content)
    db.add(row)
    db.commit()
    db.refresh(row)
    return row


def get_project_memory(db: Session, project_id: str) -> list[ProjectMemory]:
    return list(db.scalars(select(ProjectMemory).where(ProjectMemory.project_id == project_id)))
