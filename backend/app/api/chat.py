"""F10 - Workspace chat (single-agent passthrough for now)."""

from __future__ import annotations

from fastapi import APIRouter, Depends, WebSocket, WebSocketDisconnect
from sqlalchemy.orm import Session

from app.agents.graph import run_chat
from app.db import get_db
from app.models import Conversation
from app.rag.ingest import build_context_block, retrieve
from app.schemas import (
    ChatHistoryItem,
    ChatHistoryResponse,
    ChatRequest,
    ChatResponse,
)

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

    # Persist the turn when tied to a project (F10 conversation history).
    if payload.project_id:
        db.add(
            Conversation(
                project_id=payload.project_id,
                session_id=payload.session_id,
                role="user",
                content=payload.message,
            )
        )
        db.add(
            Conversation(
                project_id=payload.project_id,
                session_id=payload.session_id,
                role="assistant",
                content=result.reply,
                model=f"{result.provider}:{result.model}",
            )
        )
        db.commit()

    return ChatResponse(reply=result.reply, model=result.model, provider=result.provider)


@router.websocket("/ws")
async def chat_ws(websocket: WebSocket):
    await websocket.accept()
    db = None
    try:
        payload = await websocket.receive_json()
        # Expected payload:
        # {
        #   project_id: str | null,
        #   session_id: str | null,
        #   message: str,
        #   model: str | null,
        #   stream: boolean
        # }
        project_id = payload.get("project_id")
        session_id = payload.get("session_id")
        message = payload.get("message")
        model = payload.get("model")
        stream = bool(payload.get("stream", True))

        if not message:
            await websocket.send_json({"type": "error", "error": "Missing message"})
            return

        if stream:
            await websocket.send_json({"type": "assistant_start"})

        # Retrieve RAG context (best-effort).
        context = None
        if project_id:
            try:
                hits = retrieve(project_id, message, limit=5)
                context = build_context_block(hits) or None
            except Exception:  # noqa: BLE001
                context = None

        result = run_chat(message, model, context=context)

        # Persist the turn when tied to a project.
        if project_id:
            # Create an independent session for websocket lifespan.
            db = next(get_db())
            try:
                db.add(
                    Conversation(
                        project_id=project_id,
                        session_id=session_id,
                        role="user",
                        content=message,
                    )
                )
                db.add(
                    Conversation(
                        project_id=project_id,
                        session_id=session_id,
                        role="assistant",
                        content=result.reply,
                        model=f"{result.provider}:{result.model}",
                    )
                )
                db.commit()
            except Exception:
                db.rollback()
                raise
            finally:
                db.close()
                db = None

        if stream:
            await websocket.send_json(
                {
                    "type": "assistant_message",
                    "content": result.reply,
                    "provider": result.provider,
                    "model": result.model,
                }
            )
            await websocket.send_json({"type": "assistant_done"})
        else:
            await websocket.send_json({"type": "result", "reply": result.reply})

    except WebSocketDisconnect:
        return
    except Exception as exc:  # noqa: BLE001
        try:
            await websocket.send_json({"type": "error", "error": f"{type(exc).__name__}: {exc}"})
            await websocket.send_json({"type": "assistant_done"})
        except Exception:
            return
    finally:
        if db is not None:
            try:
                db.close()
            except Exception:
                pass


@router.get("/history", response_model=ChatHistoryResponse)
def chat_history(
    project_id: str,
    session_id: str | None = None,
    db: Session = Depends(get_db),
) -> ChatHistoryResponse:
    rows = (
        db.query(Conversation)
        .filter(Conversation.project_id == project_id)
        .filter(Conversation.session_id == session_id)
        .order_by(Conversation.created_at.asc(), Conversation.id.asc())
        .all()
    )

    return ChatHistoryResponse(
        project_id=project_id,
        session_id=session_id,
        messages=[ChatHistoryItem(role=r.role, content=r.content, model=r.model) for r in rows],
    )


@router.get("/sessions")
def chat_sessions(project_id: str, db: Session = Depends(get_db)) -> dict:
    # Distinct session ids for a project (ignore null sessions).
    # Order by last activity.
    rows = (
        db.query(Conversation.session_id, Conversation.updated_at)
        .filter(Conversation.project_id == project_id)
        .filter(Conversation.session_id.is_not(None))
        .order_by(Conversation.updated_at.desc())
        .all()
    )

    seen: set[str] = set()
    sessions: list[dict[str, str]] = []
    for session_id, _updated_at in rows:
        if not session_id:
            continue
        if session_id in seen:
            continue
        seen.add(session_id)
        sessions.append({"session_id": session_id})

    return {"project_id": project_id, "sessions": sessions}
