"""F2/F4 - Project scan, metadata, and code graph."""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.db import get_db
from app.graph.code_graph import build_code_graph
from app.models import File, Project, Service
from app.scanner.scanner import scan_project
from app.schemas import CodeGraphOut, ScanResult

router = APIRouter(prefix="/scan", tags=["scan"])


@router.post("/{project_id}", response_model=ScanResult)
def run_scan(project_id: str, db: Session = Depends(get_db)) -> ScanResult:
    project = db.get(Project, project_id)
    if project is None:
        raise HTTPException(status_code=404, detail="Project not found")

    project.scan_status = "scanning"
    db.commit()

    try:
        meta = scan_project(project.root_path)
    except FileNotFoundError as exc:
        project.scan_status = "error"
        db.commit()
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    # Replace previously-scanned file rows for this project.
    db.query(File).filter(File.project_id == project_id).delete()
    for f in meta.files[:2_000]:  # cap inserts for the scaffold
        db.add(
            File(
                project_id=project_id,
                path=f["path"],
                language=f["language"],
                size_bytes=f["size"],
            )
        )

    # Seed a couple of illustrative services so the dashboard has data.
    if not db.query(Service).filter(Service.project_id == project_id).count():
        for name in ("Auth Service", "User Service"):
            db.add(Service(project_id=project_id, name=name, health="unknown"))

    project.project_metadata = meta.to_dict()
    project.scan_status = "completed"
    db.commit()

    return ScanResult(project_id=project_id, status="completed", metadata=meta.to_dict())


@router.get("/{project_id}/metadata", response_model=ScanResult)
def get_metadata(project_id: str, db: Session = Depends(get_db)) -> ScanResult:
    project = db.get(Project, project_id)
    if project is None:
        raise HTTPException(status_code=404, detail="Project not found")
    return ScanResult(
        project_id=project_id, status=project.scan_status, metadata=project.project_metadata or {}
    )


@router.get("/{project_id}/graph", response_model=CodeGraphOut)
def get_code_graph(project_id: str, db: Session = Depends(get_db)) -> dict:
    if db.get(Project, project_id) is None:
        raise HTTPException(status_code=404, detail="Project not found")
    return build_code_graph(project_id)
