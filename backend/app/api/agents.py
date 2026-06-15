"""F5/F6 - Agents and per-agent model assignment.

On first request the seven PRD agent roles are seeded with sensible default
models (referenced as "<provider>:<model>"). Each can then be reassigned to any
provider/model independently.
"""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db import get_db
from app.models import Agent
from app.schemas import AgentModelUpdate, AgentOut

router = APIRouter(prefix="/agents", tags=["agents"])

# (role, display name, default model ref). Defaults point at stub so a fresh
# install works; swap to ollama:/anthropic:/etc. via the update endpoint.
_DEFAULT_AGENTS = [
    ("planner", "Planner Agent", "stub:echo"),
    ("architect", "Architect Agent", "stub:echo"),
    ("coding", "Coding Agent", "stub:echo"),
    ("review", "Review Agent", "stub:echo"),
    ("testing", "Testing Agent", "stub:echo"),
    ("documentation", "Documentation Agent", "stub:echo"),
    ("ocr", "OCR Agent", "stub:echo"),
]


def _seed_if_empty(db: Session) -> None:
    if db.scalar(select(Agent).limit(1)) is not None:
        return
    for role, name, model in _DEFAULT_AGENTS:
        db.add(Agent(role=role, name=name, model=model))
    db.commit()


@router.get("", response_model=list[AgentOut])
def list_agents(db: Session = Depends(get_db)) -> list[Agent]:
    _seed_if_empty(db)
    return list(db.scalars(select(Agent).order_by(Agent.role)))


@router.put("/{agent_id}/model", response_model=AgentOut)
def set_agent_model(
    agent_id: str, payload: AgentModelUpdate, db: Session = Depends(get_db)
) -> Agent:
    agent = db.get(Agent, agent_id)
    if agent is None:
        raise HTTPException(status_code=404, detail="Agent not found")
    agent.model = payload.model
    db.commit()
    db.refresh(agent)
    return agent
