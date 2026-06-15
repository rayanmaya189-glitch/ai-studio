"""F2/F4 - Project scan, metadata, and code graph."""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.db import get_db
from app.graph.code_graph import build_code_graph
from app.models import CodeGraphNode, File, Project, Service
from app.scanner.scanner import scan_project
from app.schemas import CodeGraphOut, ScanResult

router = APIRouter(prefix="/scan", tags=["scan"])

# Bound DB writes so a 500k-LOC scan doesn't try to insert a row per file.
_MAX_FILE_INSERTS = 2_000


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

    # Replace previously-scanned rows for this project (files, services, graph).
    db.query(File).filter(File.project_id == project_id).delete()
    db.query(Service).filter(Service.project_id == project_id).delete()
    db.query(CodeGraphNode).filter(CodeGraphNode.project_id == project_id).delete()

    for rec in meta.files[:_MAX_FILE_INSERTS]:
        db.add(
            File(
                project_id=project_id,
                path=rec.path,
                language=rec.language,
                size_bytes=rec.size,
            )
        )

    # Persist the services the scanner actually detected (deployable units with
    # a build marker), instead of the old hard-coded placeholders.
    for svc in meta.services:
        db.add(
            Service(
                project_id=project_id,
                name=svc["name"],
                language=svc.get("language"),
                path=svc.get("path"),
                health="unknown",
            )
        )

    project.project_metadata = meta.to_dict()
    project.scan_status = "completed"
    db.commit()

    # Build + persist the code graph from the fresh scan results.
    build_code_graph(project_id, meta, db)
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
    return build_code_graph(project_id, None, db)
