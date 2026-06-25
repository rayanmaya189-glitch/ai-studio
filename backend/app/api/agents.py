"""F5/F6 - Agents and per-agent model assignment.

On first request the seven PRD agent roles are seeded without default models.
Models must be assigned via the LLM Config page or the PUT endpoint. Each role
can be independently reassigned to any provider/model.
"""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, WebSocket, WebSocketDisconnect
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.agents.graph import _resolve_roles, iter_agent_pipeline, run_agent_pipeline
from app.db import get_db
from app.memory.store import (
    add_agent_memory,
    add_project_memory,
    get_agent_memory,
    get_project_memory,
)
from app.models import Agent
from app.providers.base import ChatMessage
from app.providers.registry import get_registry
from app.rag.ingest import build_context_block, retrieve
from app.schemas import (
    AgentModelUpdate,
    AgentOut,
    AgentRunRequest,
    AgentRunResponse,
    OcrRequest,
    OcrResponse,
    StageOut,
)

router = APIRouter(prefix="/agents", tags=["agents"])

# (role, display name, default model ref). Models are assigned via the
# LLM Config page or the PUT /agents/{id}/model endpoint.
_DEFAULT_AGENTS: list[tuple[str, str, str]] = [
    # (role, name, model_ref) — model_ref is set via the UI LLM Config page.
    # Empty string means the provider registry will fall back to the first
    # available provider's default model at runtime.
    ("planner", "Planner Agent", ""),
    ("architect", "Architect Agent", ""),
    ("coding", "Coding Agent", ""),
    ("review", "Review Agent", ""),
    ("testing", "Testing Agent", ""),
    ("documentation", "Documentation Agent", ""),
    ("ocr", "OCR Agent", ""),
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
    return list(db.scalars(select(Agent).where(Agent.project_id.is_(None)).order_by(Agent.role)))


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


_OCR_SYSTEM_PROMPT = (
    "You are the OCR / document-extraction agent. Given text extracted from a "
    "document or a description of a diagram, produce clean, structured output: "
    "extract entities, relationships, and key facts as well-formatted markdown. "
    "Do not invent content that is not present in the input."
)


@router.post("/ocr", response_model=OcrResponse)
def run_ocr(payload: OcrRequest, db: Session = Depends(get_db)) -> OcrResponse:
    """Run the OCR/document-extraction agent on already-extracted text (F5 OCR).

    OCR is vision work and runs as its own endpoint, separate from the dev
    pipeline. This text-in path lets the OCR agent structure extracted document
    text now; raw-image vision input is a follow-up needing a vision provider.
    """
    _seed_if_empty(db)
    model_ref = payload.model
    if not model_ref:
        ocr_agent = db.scalar(
            select(Agent).where(Agent.project_id.is_(None), Agent.role == "ocr")
        )
        model_ref = ocr_agent.model if ocr_agent and ocr_agent.model else None

    registry = get_registry()
    try:
        provider, model = registry.resolve(model_ref)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    messages = [
        ChatMessage(role="system", content=_OCR_SYSTEM_PROMPT),
        ChatMessage(role="user", content=f"{payload.instruction}\n\n---\n{payload.content}"),
    ]
    try:
        output = provider.chat(messages, model)
    except Exception as exc:  # noqa: BLE001 - surface provider failure cleanly
        raise HTTPException(status_code=502, detail=f"OCR provider failed: {exc}") from exc

    return OcrResponse(provider=provider.name, model=model, output=output)


@router.post("/run", response_model=AgentRunResponse)
def run_pipeline(payload: AgentRunRequest, db: Session = Depends(get_db)) -> AgentRunResponse:
    """Run the autonomous Planner->Architect->Coding->Review->Testing chain (F11)."""
    model_map, context, project_memory, agent_memory_map = _build_pipeline_inputs(
        db, payload.goal, payload.project_id, payload.model_map
    )

    result = run_agent_pipeline(
        payload.goal,
        model_map=model_map,
        context=context,
        project_memory=project_memory,
        agent_memory_map=agent_memory_map,
        roles=payload.roles,
    )

    # Write each stage back to its own agent's private memory, then record the
    # run in shared project memory (history) so project chatbots stay aware of
    # what the pipeline planned/built. Both are best-effort.
    agent_ids = _pipeline_agent_ids(db)
    for stage in result.stages:
        _record_stage_memory(
            db, agent_ids, payload.project_id, payload.goal, stage.role, stage.output, stage.error
        )
    if payload.project_id:
        _record_pipeline_history(db, payload.project_id, payload.goal, result.final_output)

    return AgentRunResponse(
        goal=result.goal,
        stages=[StageOut(**vars(s)) for s in result.stages],
        final_output=result.final_output,
    )


def _build_pipeline_inputs(
    db: Session, goal: str, project_id: str | None, model_map: dict[str, str] | None
) -> tuple[dict[str, str], str | None, str | None, dict[str, str]]:
    """Assemble the model map + RAG context + memories for a pipeline run.

    Shared by the REST (``POST /run``) and WebSocket (``/run/ws``) paths so both
    ground the pipeline identically. All retrieval is best-effort: a failure in
    any layer yields ``None``/empty rather than aborting the run.
    """
    _seed_if_empty(db)
    pipeline_agents = list(db.scalars(select(Agent).where(Agent.project_id.is_(None))))
    resolved_map = {a.role: a.model for a in pipeline_agents}
    if model_map:
        resolved_map.update(model_map)

    context = None
    project_memory = None
    agent_memory_map: dict[str, str] = {}

    if project_id:
        try:
            hits = retrieve(project_id, goal, limit=5)
            context = build_context_block(hits) or None
        except Exception:  # noqa: BLE001 - retrieval is best-effort
            context = None

        try:
            pm = get_project_memory(db, project_id)
            if pm:
                project_memory = "\n".join(f"[{m.category}] {m.title}\n{m.content}" for m in pm)
        except Exception:  # noqa: BLE001 - memory is best-effort
            project_memory = None

        try:
            for agent in pipeline_agents:
                mem = get_agent_memory(db, agent.id)
                if mem:
                    agent_memory_map[agent.role] = "\n".join(f"[{m.kind}] {m.content}" for m in mem)
        except Exception:  # noqa: BLE001 - memory is best-effort
            agent_memory_map = {}

    return resolved_map, context, project_memory, agent_memory_map


def _record_pipeline_history(db: Session, project_id: str, goal: str, final_output: str) -> None:
    """Persist a completed run to shared project memory (best-effort)."""
    if not final_output:
        return
    try:
        add_project_memory(
            db,
            project_id=project_id,
            category="history",
            title=f"Pipeline run: {goal[:120]}",
            content=final_output[:4000],
        )
    except Exception:  # noqa: BLE001 - recording is best-effort
        pass


def _pipeline_agent_ids(db: Session) -> dict[str, str]:
    """Map each global pipeline role to its Agent id (for write-back memory)."""
    return {a.role: a.id for a in db.scalars(select(Agent).where(Agent.project_id.is_(None)))}


def _record_stage_memory(
    db: Session,
    agent_ids: dict[str, str],
    project_id: str | None,
    goal: str,
    role: str,
    output: str,
    error: str | None,
) -> None:
    """Append one stage's output to its own agent's private memory (best-effort).

    This is the *write-during-run* half of agent memory: each role accumulates
    notes from the runs it participated in, so a later run's ``agent_memory_map``
    (see :func:`_build_pipeline_inputs`) feeds that history back into the prompt.
    Failed or empty stages are skipped — there's nothing worth remembering.
    """
    agent_id = agent_ids.get(role)
    if not agent_id or error or not output.strip():
        return
    try:
        add_agent_memory(
            db,
            agent_id=agent_id,
            content=f"Goal: {goal[:120]}\n{output[:2000]}",
            kind="pipeline",
            project_id=project_id,
        )
    except Exception:  # noqa: BLE001 - recording is best-effort
        pass


@router.websocket("/run/ws")
async def run_pipeline_ws(websocket: WebSocket) -> None:
    """Stream a pipeline run stage-by-stage (F11).

    Client sends a single JSON payload: ``{ goal, project_id?, model_map? }``.

    Server emits, in order:
      - ``{ type: "pipeline_start", roles: [...] }`` — before the first stage
      - ``{ type: "pipeline_stage", stage: { role, provider, model, output, error } }``
        once per stage, as soon as that stage completes
      - ``{ type: "pipeline_done", final_output }`` — after the last stage
      - ``{ type: "error", error }`` — on a fatal error (bad payload, no provider)
    """
    await websocket.accept()
    db = None
    try:
        payload = await websocket.receive_json()
        goal = payload.get("goal")
        project_id = payload.get("project_id")
        model_map = payload.get("model_map") or None
        roles = payload.get("roles") or None

        if not goal:
            await websocket.send_json({"type": "error", "error": "Missing goal"})
            return

        db = next(get_db())
        resolved_map, context, project_memory, agent_memory_map = _build_pipeline_inputs(
            db, goal, project_id, model_map
        )

        active_roles = _resolve_roles(roles)
        await websocket.send_json({"type": "pipeline_start", "roles": list(active_roles)})

        agent_ids = _pipeline_agent_ids(db)
        final_output = ""
        for stage in iter_agent_pipeline(
            goal,
            model_map=resolved_map,
            context=context,
            project_memory=project_memory,
            agent_memory_map=agent_memory_map,
            roles=roles,
        ):
            final_output = stage.output or final_output
            # Write-during-run: persist each stage to its agent's memory as soon
            # as it completes, before streaming it to the client.
            _record_stage_memory(
                db, agent_ids, project_id, goal, stage.role, stage.output, stage.error
            )
            await websocket.send_json(
                {
                    "type": "pipeline_stage",
                    "stage": {
                        "role": stage.role,
                        "provider": stage.provider,
                        "model": stage.model,
                        "output": stage.output,
                        "error": stage.error,
                    },
                }
            )

        # The last stage's output is the pipeline result (mirrors PipelineResult).
        if project_id:
            _record_pipeline_history(db, project_id, goal, final_output)

        await websocket.send_json({"type": "pipeline_done", "final_output": final_output})

    except WebSocketDisconnect:
        return
    except Exception as exc:  # noqa: BLE001
        try:
            await websocket.send_json({"type": "error", "error": f"{type(exc).__name__}: {exc}"})
        except Exception:  # noqa: BLE001 - client already gone
            return
    finally:
        if db is not None:
            try:
                db.close()
            except Exception:  # noqa: BLE001
                pass
