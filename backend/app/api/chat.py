"""F10 - Workspace chat (single-agent passthrough for now)."""

from __future__ import annotations

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.agents.graph import run_chat
from app.db import get_db
from app.models import Conversation
from app.schemas import ChatRequest, ChatResponse

router = APIRouter(prefix="/chat", tags=["chat"])


@router.post("", response_model=ChatResponse)
def chat(payload: ChatRequest, db: Session = Depends(get_db)) -> ChatResponse:
    result = run_chat(payload.message, payload.model)

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
