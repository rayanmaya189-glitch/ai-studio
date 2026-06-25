"""Project-scoped custom agents / chatbots.

These are agents the user creates *inside a project*: a named assistant with its
own model and system prompt that you chat with to solve issues and answer
queries about that specific codebase.

Grounding model (anti-hallucination):
- environment facts  — pulled from the project's scan metadata (services, langs,
  databases, endpoint counts) so the agent knows what actually exists.
- retrieved code     — RAG hits for the user's message.
- private memory     — this agent's own AgentMemory rows (its folder/notes).
- shared memory      — the project's ProjectMemory (the single shared place both
  the pipeline agents and every chatbot read and write), so when one agent
  solves or builds something, the others become aware of it.
"""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.agents.graph import run_grounded_chat
from app.db import get_db
from app.memory.store import (
    add_agent_memory,
    add_project_memory,
    get_agent_memory,
    get_project_memory,
)
from app.models import Agent, Conversation, Project
from app.providers.base import ChatMessage
from app.rag.ingest import build_context_block, retrieve
from app.schemas import (
    AgentChatRequest,
    AgentChatResponse,
    ProjectAgentCreate,
    ProjectAgentOut,
    ProjectAgentUpdate,
)

router = APIRouter(prefix="/projects/{project_id}/agents", tags=["project-agents"])


def _require_project(db: Session, project_id: str) -> Project:
    project = db.get(Project, project_id)
    if project is None:
        raise HTTPException(status_code=404, detail="Project not found")
    return project


def _require_custom_agent(db: Session, project_id: str, agent_id: str) -> Agent:
    agent = db.get(Agent, agent_id)
    if agent is None or agent.project_id != project_id or agent.kind != "custom":
        raise HTTPException(status_code=404, detail="Project agent not found")
    return agent


def _env_facts(project: Project) -> str:
    """Render the project's scan metadata into a compact, factual block."""
    m = project.project_metadata or {}
    if not m:
        return ""
    lines: list[str] = [f"Project root: {project.root_path}"]
    for label, key in (
        ("Files", "file_count"),
        ("Services", "service_count"),
        ("Endpoints", "endpoint_count"),
        ("Symbols", "symbol_count"),
        ("Databases", "database_count"),
    ):
        if key in m:
            lines.append(f"{label}: {m[key]}")
    langs = m.get("languages") or {}
    if langs:
        lines.append("Languages: " + ", ".join(f"{k}={v}" for k, v in langs.items()))
    services = m.get("services") or []
    if services:
        names = ", ".join(s.get("name", "?") for s in services[:30])
        lines.append(f"Service names: {names}")
    databases = m.get("databases") or []
    if databases:
        lines.append("Databases detected: " + ", ".join(databases))
    return "\n".join(lines)


# ---- CRUD ----
@router.get("", response_model=list[ProjectAgentOut])
def list_project_agents(project_id: str, db: Session = Depends(get_db)) -> list[Agent]:
    _require_project(db, project_id)
    return list(
        db.scalars(
            select(Agent)
            .where(Agent.project_id == project_id, Agent.kind == "custom")
            .order_by(Agent.created_at)
        )
    )


@router.post("", response_model=ProjectAgentOut)
def create_project_agent(
    project_id: str, payload: ProjectAgentCreate, db: Session = Depends(get_db)
) -> Agent:
    _require_project(db, project_id)
    agent = Agent(
        project_id=project_id,
        kind="custom",
        role="custom",
        name=payload.name,
        model=payload.model,
        description=payload.description,
        system_prompt=payload.system_prompt,
    )
    db.add(agent)
    db.commit()
    db.refresh(agent)
    return agent


@router.patch("/{agent_id}", response_model=ProjectAgentOut)
def update_project_agent(
    project_id: str, agent_id: str, payload: ProjectAgentUpdate, db: Session = Depends(get_db)
) -> Agent:
    agent = _require_custom_agent(db, project_id, agent_id)
    if payload.name is not None:
        agent.name = payload.name
    if payload.model is not None:
        agent.model = payload.model
    if payload.description is not None:
        agent.description = payload.description
    if payload.system_prompt is not None:
        agent.system_prompt = payload.system_prompt
    db.commit()
    db.refresh(agent)
    return agent


@router.delete("/{agent_id}")
def delete_project_agent(project_id: str, agent_id: str, db: Session = Depends(get_db)) -> dict:
    agent = _require_custom_agent(db, project_id, agent_id)
    db.delete(agent)
    db.commit()
    return {"deleted": agent_id}


# ---- Private memory (this agent's own folder/notes) ----
@router.get("/{agent_id}/memory")
def list_agent_private_memory(
    project_id: str, agent_id: str, db: Session = Depends(get_db)
) -> list[dict]:
    _require_custom_agent(db, project_id, agent_id)
    return [
        {"id": m.id, "kind": m.kind, "content": m.content, "created_at": m.created_at.isoformat()}
        for m in get_agent_memory(db, agent_id)
    ]


# ---- Grounded chat ----
@router.post("/{agent_id}/chat", response_model=AgentChatResponse)
def chat_with_project_agent(
    project_id: str, agent_id: str, payload: AgentChatRequest, db: Session = Depends(get_db)
) -> AgentChatResponse:
    project = _require_project(db, project_id)
    agent = _require_custom_agent(db, project_id, agent_id)

    # 1. Environment facts from the scan (what actually exists).
    env_facts = _env_facts(project) or None

    # 2. Retrieved code for this message (best-effort).
    context = None
    try:
        hits = retrieve(project_id, payload.message, limit=5)
        context = build_context_block(hits) or None
    except Exception:  # noqa: BLE001 - retrieval is best-effort
        context = None

    # 3. This agent's private memory.
    private_memory = None
    try:
        mem = get_agent_memory(db, agent_id)
        if mem:
            private_memory = "\n".join(f"[{m.kind}] {m.content}" for m in mem)
    except Exception:  # noqa: BLE001 - best-effort
        private_memory = None

    # 4. Shared project memory (what every agent has decided/done).
    shared_memory = None
    try:
        pm = get_project_memory(db, project_id)
        if pm:
            shared_memory = "\n".join(f"[{m.category}] {m.title}\n{m.content}" for m in pm)
    except Exception:  # noqa: BLE001 - best-effort
        shared_memory = None

    # 5. Recent conversation history for this agent (kept short).
    history: list[ChatMessage] = []
    try:
        rows = list(
            db.scalars(
                select(Conversation)
                .where(
                    Conversation.project_id == project_id,
                    Conversation.model == f"agent:{agent_id}",
                )
                .order_by(Conversation.created_at.desc())
                .limit(8)
            )
        )
        for row in reversed(rows):
            role = "user" if row.role == "user" else "assistant"
            history.append(ChatMessage(role=role, content=row.content))
    except Exception:  # noqa: BLE001 - best-effort
        history = []

    result = run_grounded_chat(
        payload.message,
        agent.model,
        system_prompt=agent.system_prompt,
        env_facts=env_facts,
        context=context,
        private_memory=private_memory,
        shared_memory=shared_memory,
        history=history,
    )

    if payload.remember:
        # Persist the turn as conversation (tagged to this agent) and as the
        # agent's private memory so it remembers across sessions.
        db.add(
            Conversation(
                project_id=project_id,
                role="user",
                content=payload.message,
                model=f"agent:{agent_id}",
            )
        )
        db.add(
            Conversation(
                project_id=project_id,
                role="assistant",
                content=result.reply,
                model=f"agent:{agent_id}",
            )
        )
        db.commit()
        try:
            add_agent_memory(
                db,
                agent_id=agent_id,
                content=f"Q: {payload.message}\nA: {result.reply}"[:4000],
                kind="chat",
                project_id=project_id,
            )
        except Exception:  # noqa: BLE001 - best-effort
            pass

    return AgentChatResponse(
        reply=result.reply,
        provider=result.provider,
        model=result.model,
        used_context=result.used_context,
        used_private_memory=result.used_private_memory,
        used_shared_memory=result.used_shared_memory,
    )


# ---- Promote a solution to shared memory ----
@router.post("/{agent_id}/share")
def share_to_project_memory(
    project_id: str,
    agent_id: str,
    payload: dict,
    db: Session = Depends(get_db),
) -> dict:
    """Let an agent publish a solution/decision to the shared project memory.

    This is how a chatbot makes the rest of the team aware it solved or built
    something. ``payload`` accepts ``category`` (default ``history``), ``title``,
    and ``content``.
    """
    _require_custom_agent(db, project_id, agent_id)
    title = payload.get("title")
    content = payload.get("content")
    if not title or not content:
        raise HTTPException(status_code=400, detail="title and content are required")
    category = payload.get("category", "history")
    try:
        row = add_project_memory(
            db, project_id=project_id, category=category, title=title, content=content
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return {"id": row.id, "category": row.category, "title": row.title}
