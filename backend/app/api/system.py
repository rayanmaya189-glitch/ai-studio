"""System readiness and runtime status for production deployments."""

from __future__ import annotations

from fastapi import APIRouter, Depends
from sqlalchemy import text
from sqlalchemy.orm import Session

from app.db import get_db
from app.providers import get_registry
from app.schemas import SystemStatusOut

router = APIRouter(tags=["system"])


@router.get("/ready", response_model=SystemStatusOut)
def readiness(db: Session = Depends(get_db)) -> SystemStatusOut:
    db_health = "ok"
    detail: str | None = None
    ready = True

    try:
        db.execute(text("SELECT 1"))
    except Exception as exc:  # noqa: BLE001 - readiness must never leak a stack trace
        db_health = "error"
        detail = str(exc)
        ready = False

    registry = get_registry()
    enabled = 0
    try:
        enabled = sum(1 for provider in registry.all() if provider.available())
    except Exception as exc:  # noqa: BLE001 - report degraded readiness cleanly
        detail = detail or str(exc)
        ready = False

    if enabled == 0:
        ready = False
        detail = detail or "No enabled LLM providers are available. Configure one in LLM Config."

    return SystemStatusOut(
        status="ok" if ready else "degraded",
        service="ads-backend",
        version="0.1.0",
        database=db_health,
        providers_enabled=enabled,
        ready=ready,
        detail=detail,
    )
