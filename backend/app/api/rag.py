"""F3 - RAG semantic search over a project's ingested vectors."""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.db import get_db
from app.models import Project
from app.rag.ingest import retrieve
from app.schemas import RagHit, RagSearchRequest, RagSearchResponse

router = APIRouter(prefix="/rag", tags=["rag"])


@router.post("/{project_id}/search", response_model=RagSearchResponse)
def search(
    project_id: str, payload: RagSearchRequest, db: Session = Depends(get_db)
) -> RagSearchResponse:
    if db.get(Project, project_id) is None:
        raise HTTPException(status_code=404, detail="Project not found")

    chunks = retrieve(project_id, payload.query, limit=payload.limit)
    hits = [
        RagHit(
            source_path=c.source_path,
            score=c.score,
            text=c.text,
            start_line=c.start_line,
            end_line=c.end_line,
            symbols=c.symbols,
        )
        for c in chunks
    ]
    return RagSearchResponse(project_id=project_id, hits=hits)
