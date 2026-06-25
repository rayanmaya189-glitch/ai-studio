"""F12 - Code editing (scaffold).

This is a minimal, safe-enough file write endpoint to support an editor/diff
UI without wiring a full git/PR workflow yet.

- Applies file contents under the project's `root_path`
- Basic path traversal protection: the resolved target must stay within root
"""

from __future__ import annotations

import os

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app.db import get_db
from app.models import Project
from app.schemas import EditApplyRequest, EditApplyResponse, FileReadResponse

router = APIRouter(prefix="/edit", tags=["edit"])

# Cap single-file reads so the editor never tries to load a huge/binary blob.
_MAX_READ_BYTES = 1_000_000


def _resolve_under_root(root_path: str, rel_path: str) -> str:
    # Normalize and strip any leading separators to keep it “relative”.
    rel_path = rel_path.lstrip("/\\")
    target = os.path.abspath(os.path.join(root_path, rel_path))
    root_abs = os.path.abspath(root_path)
    if os.path.commonpath([root_abs, target]) != root_abs:
        raise ValueError(f"Path traversal blocked: {rel_path!r}")
    return target


@router.get("/{project_id}/file", response_model=FileReadResponse)
def read_file(
    project_id: str,
    path: str = Query(..., description="Path relative to the project root"),
    db: Session = Depends(get_db),
) -> FileReadResponse:
    """Read a single text file under the project root (for the editor/diff UI)."""
    project = db.get(Project, project_id)
    if project is None:
        raise HTTPException(status_code=404, detail="Project not found")

    try:
        target = _resolve_under_root(project.root_path, path)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    if not os.path.isfile(target):
        raise HTTPException(status_code=404, detail=f"File not found: {path}")

    size = os.path.getsize(target)
    truncated = size > _MAX_READ_BYTES
    try:
        with open(target, encoding="utf-8", errors="replace") as fh:
            content = fh.read(_MAX_READ_BYTES)
    except OSError as exc:
        raise HTTPException(status_code=400, detail=f"Cannot read file: {exc}") from exc

    return FileReadResponse(path=path, content=content, size_bytes=size, truncated=truncated)


@router.post("/{project_id}/apply", response_model=EditApplyResponse)
def apply_edits(
    project_id: str, payload: EditApplyRequest, db: Session = Depends(get_db)
) -> EditApplyResponse:
    project = db.get(Project, project_id)
    if project is None:
        raise HTTPException(status_code=404, detail="Project not found")

    applied = 0
    errors: list[str] = []

    for edit in payload.edits:
        try:
            target = _resolve_under_root(project.root_path, edit.path)
            os.makedirs(os.path.dirname(target), exist_ok=True)
            with open(target, "w", encoding="utf-8") as fh:
                fh.write(edit.content)
            applied += 1
        except Exception as exc:  # noqa: BLE001
            errors.append(f"{edit.path}: {type(exc).__name__}: {exc}")

    return EditApplyResponse(applied=applied, errors=errors)
