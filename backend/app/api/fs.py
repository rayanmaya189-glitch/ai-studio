"""Filesystem browser for picking project/workspace folders.

The studio is a local-first, self-hosted tool, so the picker browses the host's
real filesystem. ``GET /fs/list`` returns the directories (and optionally files)
under a path; the UI uses it to navigate in/out and select a folder for a
project or workspace. Reads are best-effort: unreadable entries are skipped
rather than failing the whole listing, and a bad path returns a 400.
"""

from __future__ import annotations

import os
from pathlib import Path

from fastapi import APIRouter, HTTPException, Query

from app.schemas import FsEntry, FsListing

router = APIRouter(prefix="/fs", tags=["fs"])


def _home() -> Path:
    return Path(os.path.expanduser("~")).resolve()


def _safe_is_dir(p: Path) -> bool:
    try:
        return p.is_dir()
    except OSError:
        return False


@router.get("/list", response_model=FsListing)
def list_dir(
    path: str | None = Query(default=None, description="Absolute dir to list; defaults to $HOME"),
    show_hidden: bool = Query(default=False, description="Include dot-entries"),
    include_files: bool = Query(default=True, description="Include files, not just folders"),
) -> FsListing:
    """List the immediate children of ``path`` (defaults to the home folder)."""
    target = Path(path).expanduser() if path else _home()

    try:
        target = target.resolve()
    except OSError as exc:  # pragma: no cover - exotic FS errors
        raise HTTPException(status_code=400, detail=f"Invalid path: {exc}") from exc

    if not target.exists():
        raise HTTPException(status_code=404, detail=f"Path does not exist: {target}")
    if not _safe_is_dir(target):
        raise HTTPException(status_code=400, detail=f"Not a directory: {target}")

    entries: list[FsEntry] = []
    try:
        with os.scandir(target) as it:
            for entry in it:
                name = entry.name
                if not show_hidden and name.startswith("."):
                    continue
                try:
                    is_dir = entry.is_dir(follow_symlinks=False) or entry.is_dir()
                except OSError:
                    continue
                if not is_dir and not include_files:
                    continue
                entries.append(FsEntry(name=name, path=str(Path(entry.path).resolve()), is_dir=is_dir))
    except PermissionError as exc:
        raise HTTPException(status_code=403, detail=f"Permission denied: {target}") from exc

    # Directories first, then files; each group alphabetical (case-insensitive).
    entries.sort(key=lambda e: (not e.is_dir, e.name.lower()))

    parent = str(target.parent) if target.parent != target else None
    return FsListing(path=str(target), parent=parent, home=str(_home()), entries=entries)
