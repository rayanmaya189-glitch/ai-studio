"""F1 - Project selection and listing."""

from __future__ import annotations

from pathlib import Path

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db import get_db
from app.models import Project
from app.schemas import ProjectCreate, ProjectOut

router = APIRouter(prefix="/projects", tags=["projects"])


def _normalize_project_root(root_path: str) -> str:
    try:
        resolved = Path(root_path).expanduser().resolve(strict=True)
    except FileNotFoundError as exc:
        raise HTTPException(status_code=400, detail=f"Project path does not exist: {root_path}") from exc
    except OSError as exc:
        raise HTTPException(status_code=400, detail=f"Invalid project path: {exc}") from exc

    if not resolved.is_dir():
        raise HTTPException(status_code=400, detail=f"Project path is not a directory: {resolved}")

    return str(resolved)


@router.post("", response_model=ProjectOut)
def create_project(payload: ProjectCreate, db: Session = Depends(get_db)) -> Project:
    normalized_root = _normalize_project_root(payload.root_path)

    existing = db.scalar(select(Project).where(Project.root_path == normalized_root))
    if existing is not None:
        raise HTTPException(status_code=409, detail="A project for this folder already exists")

    project = Project(name=payload.name, root_path=normalized_root)
    db.add(project)
    db.commit()
    db.refresh(project)
    return project


@router.get("", response_model=list[ProjectOut])
def list_projects(db: Session = Depends(get_db)) -> list[Project]:
    return list(db.scalars(select(Project).order_by(Project.created_at.desc())))


@router.get("/{project_id}", response_model=ProjectOut)
def get_project(project_id: str, db: Session = Depends(get_db)) -> Project:
    project = db.get(Project, project_id)
    if project is None:
        raise HTTPException(status_code=404, detail="Project not found")
    return project
