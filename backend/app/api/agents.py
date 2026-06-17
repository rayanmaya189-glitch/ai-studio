"""F5/F6 - Agents and per-agent model assignment.

On first request the seven PRD agent roles are seeded with sensible default
models (referenced as "<provider>:<model>"). Each can then be reassigned to any
provider/model independently.
"""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.agents.graph import run_agent_pipeline
from app.db import get_db
from app.memory.store import add_project_memory, get_agent_memory, get_project_memory
from app.models import Agent
from app.rag.ingest import build_context_block, retrieve
from app.schemas import (
    AgentModelUpdate,
    AgentOut,
    AgentRunRequest,
    AgentRunResponse,
    StageOut,
)

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
    # Only the global pipeline roles (project_id IS NULL) are seeded; custom
    # project agents are created explicitly by the user.
    if db.scalar(select(Agent).where(Agent.project_id.is_(None)).limit(1)) is not None:
        return
    for role, name, model in _DEFAULT_AGENTS:
        db.add(Agent(role=role, name=name, model=model, kind="pipeline"))
    db.commit()


@router.get("", response_model=list[AgentOut])
def list_agents(db: Session = Depends(get_db)) -> list[Agent]:
    _seed_if_empty(db)
    return list(
        db.scalars(
            select(Agent).where(Agent.project_id.is_(None)).order_by(Agent.role)
        )
    )


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


@router.post("/run", response_model=AgentRunResponse)
def run_pipeline(payload: AgentRunRequest, db: Session = Depends(get_db)) -> AgentRunResponse:
    """Run the autonomous Planner->Architect->Coding->Review->Testing chain (F11).

    The per-role model map is built from the Agent table (each role on its own
    assigned model), with any ``model_map`` entries in the request taking
    precedence. When a ``project_id`` is given, RAG context is retrieved and
    threaded into every stage's prompt.
    """
    _seed_if_empty(db)
    pipeline_agents = list(db.scalars(select(Agent).where(Agent.project_id.is_(None))))
    model_map = {a.role: a.model for a in pipeline_agents}
    if payload.model_map:
        model_map.update(payload.model_map)

    # Retrieve RAG + memories (best-effort — failures yield none).
    context = None
    project_memory = None
    agent_memory_map: dict[str, str] = {}

    if payload.project_id:
        # RAG context
        try:
            hits = retrieve(payload.project_id, payload.goal, limit=5)
            context = build_context_block(hits) or None
        except Exception:  # noqa: BLE001 - retrieval is best-effort
            context = None

        # Project memory
        try:
            pm = get_project_memory(db, payload.project_id)
            if pm:
                project_memory = "\n".join(f"[{m.category}] {m.title}\n{m.content}" for m in pm)
        except Exception:  # noqa: BLE001 - memory is best-effort
            project_memory = None

        # Agent memory per role (pipeline agents only)
        try:
            for agent in pipeline_agents:
                mem = get_agent_memory(db, agent.id)
                if mem:
                    agent_memory_map[agent.role] = "\n".join(
                        f"[{m.kind}] {m.content}" for m in mem
                    )
        except Exception:  # noqa: BLE001 - memory is best-effort
            agent_memory_map = {}

    result = run_agent_pipeline(
        payload.goal,
        model_map=model_map,
        context=context,
        project_memory=project_memory,
        agent_memory_map=agent_memory_map,
    )

    # Record the run in shared project memory (history) so project chatbots stay
    # aware of what the pipeline planned/built — the "one shared place" both
    # pipeline agents and custom chatbots read from. Best-effort.
    if payload.project_id and result.final_output:
        try:
            add_project_memory(
                db,
                project_id=payload.project_id,
                category="history",
                title=f"Pipeline run: {payload.goal[:120]}",
                content=result.final_output[:4000],
            )
        except Exception:  # noqa: BLE001 - recording is best-effort
            pass

    return AgentRunResponse(
        goal=result.goal,
        stages=[StageOut(**vars(s)) for s in result.stages],
        final_output=result.final_output,
    )
