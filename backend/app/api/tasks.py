"""F9 - Task management (create, assign, track, status)."""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db import get_db
from app.models import Project, Task
from app.schemas import TaskCreate, TaskOut, TaskUpdate

router = APIRouter(prefix="/projects/{project_id}/tasks", tags=["tasks"])

_VALID_STATES = {"pending", "in_progress", "blocked", "completed"}


@router.post("", response_model=TaskOut)
def create_task(project_id: str, payload: TaskCreate, db: Session = Depends(get_db)) -> Task:
    if db.get(Project, project_id) is None:
        raise HTTPException(status_code=404, detail="Project not found")
    task = Task(
        project_id=project_id,
        title=payload.title,
        description=payload.description,
        assigned_agent_id=payload.assigned_agent_id,
    )
    db.add(task)
    db.commit()
    db.refresh(task)
    return task


@router.get("", response_model=list[TaskOut])
def list_tasks(project_id: str, db: Session = Depends(get_db)) -> list[Task]:
    return list(db.scalars(select(Task).where(Task.project_id == project_id)))


@router.patch("/{task_id}", response_model=TaskOut)
def update_task(
    project_id: str, task_id: str, payload: TaskUpdate, db: Session = Depends(get_db)
) -> Task:
    task = db.get(Task, task_id)
    if task is None or task.project_id != project_id:
        raise HTTPException(status_code=404, detail="Task not found")
    if payload.status is not None and payload.status not in _VALID_STATES:
        raise HTTPException(status_code=400, detail=f"Invalid status: {payload.status}")

    for field, value in payload.model_dump(exclude_unset=True).items():
        setattr(task, field, value)
    db.commit()
    db.refresh(task)
    return task
