"""F10 - Workspace chat (single-agent passthrough for now)."""

from __future__ import annotations

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.agents.graph import run_chat
from app.db import get_db
from app.models import Conversation
from app.rag.ingest import build_context_block, retrieve
from app.schemas import ChatRequest, ChatResponse

router = APIRouter(prefix="/chat", tags=["chat"])


@router.post("", response_model=ChatResponse)
def chat(payload: ChatRequest, db: Session = Depends(get_db)) -> ChatResponse:
    # Retrieve project-specific context from the RAG store so the agent answers
    # against the user's actual codebase. Best-effort: failures yield no context.
    context = None
    if payload.project_id:
        try:
            hits = retrieve(payload.project_id, payload.message, limit=5)
            context = build_context_block(hits) or None
        except Exception:  # noqa: BLE001 - retrieval is best-effort
            context = None

    result = run_chat(payload.message, payload.model, context=context)

    # Persist the turn when tied to a project (F8 conversation history).
    if payload.project_id:
        db.add(Conversation(project_id=payload.project_id, role="user", content=payload.message))
        db.add(
            Conversation(
                project_id=payload.project_id,
                role="assistant",
                content=result.reply,
                model=f"{result.provider}:{result.model}",
            )
        )
        db.commit()

    return ChatResponse(reply=result.reply, model=result.model, provider=result.provider)
