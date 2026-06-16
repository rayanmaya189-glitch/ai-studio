"""F12 - Code editing (scaffold).

This is a minimal, safe-enough file write endpoint to support an editor/diff
UI without wiring a full git/PR workflow yet.

- Applies file contents under the project's `root_path`
- Basic path traversal protection: the resolved target must stay within root
"""
from __future__ import annotations

import os
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.db import get_db
from app.models import Project
from app.schemas import EditApplyRequest, EditApplyResponse

router = APIRouter(prefix="/edit", tags=["edit"])


def _resolve_under_root(root_path: str, rel_path: str) -> str:
    # Normalize and strip any leading separators to keep it “relative”.
    rel_path = rel_path.lstrip("/\\")
    target = os.path.abspath(os.path.join(root_path, rel_path))
    root_abs = os.path.abspath(root_path)
    if os.path.commonpath([root_abs, target]) != root_abs:
        raise ValueError(f"Path traversal blocked: {rel_path!r}")
    return target


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
