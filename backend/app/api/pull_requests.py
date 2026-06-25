"""F13 - Pull request generator (scaffold).

This endpoint generates a PR description using an LLM. For now, it is a
best-effort scaffold that can run with the `stub` provider (zero config).

Later versions can:
- create git commits/branches
- produce file diffs from the edit apply step
- open real PRs via a provider (GitHub/GitLab)
"""

from __future__ import annotations

import os

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.agents.graph import run_chat
from app.api.edit import _resolve_under_root
from app.db import get_db
from app.git_ops import GitError, commit_edits, current_branch, is_git_repo
from app.models import Project
from app.schemas import (
    GitStatusResponse,
    PullRequestCommitRequest,
    PullRequestCommitResponse,
    PullRequestGenerateRequest,
    PullRequestGenerateResponse,
)

router = APIRouter(prefix="/projects", tags=["pull-requests"])


def _require_project(db: Session, project_id: str) -> Project:
    project = db.get(Project, project_id)
    if project is None:
        raise HTTPException(status_code=404, detail="Project not found")
    return project


@router.post("/{project_id}/pull-requests/generate", response_model=PullRequestGenerateResponse)
def generate_pr(
    project_id: str,
    payload: PullRequestGenerateRequest,
    db: Session = Depends(get_db),
) -> PullRequestGenerateResponse:
    project = _require_project(db, project_id)

    # For v0: just ask the LLM for a structured-ish PR description.
    prompt = (
        f"Generate a pull request description for the following change request.\n"
        f"Title: {payload.title}\n"
        f"Summary goal: {payload.summary_goal}\n\n"
        "Return:\n"
        "- A concise PR summary\n"
        "- Motivation\n"
        "- Implementation details (bullets)\n"
        "- Testing notes (bullets)\n"
        "- Risk/rollback notes\n"
        f"Project name: {project.name}\n"
    )

    # payload.model can be provided as "<provider>:<model>" override; otherwise default.
    model_ref = payload.model

    # No RAG context in this scaffold yet (can be added once edit/diff outputs exist).
    result = run_chat(prompt, model_ref=model_ref, context=None)

    return PullRequestGenerateResponse(
        project_id=project_id,
        title=payload.title,
        provider=result.provider,
        model=result.model,
        description=result.reply,
    )


@router.get("/{project_id}/git/status", response_model=GitStatusResponse)
def git_status(project_id: str, db: Session = Depends(get_db)) -> GitStatusResponse:
    """Report whether the project's folder is a git repo and its current branch."""
    project = _require_project(db, project_id)
    if not is_git_repo(project.root_path):
        return GitStatusResponse(is_git_repo=False, detail="Folder is not a git repository")
    try:
        return GitStatusResponse(is_git_repo=True, branch=current_branch(project.root_path))
    except GitError as exc:
        return GitStatusResponse(is_git_repo=True, detail=str(exc))


@router.post("/{project_id}/pull-requests/commit", response_model=PullRequestCommitResponse)
def commit_pull_request(
    project_id: str,
    payload: PullRequestCommitRequest,
    db: Session = Depends(get_db),
) -> PullRequestCommitResponse:
    """Write the given edits, commit them on a new branch, and return the real diff.

    This is the production F13 path: a real git branch + commit + ``git diff``,
    plus an optional LLM-generated PR description. Pushing / opening a hosted PR
    is intentionally out of scope (needs a host token).
    """
    project = _require_project(db, project_id)

    if not is_git_repo(project.root_path):
        raise HTTPException(
            status_code=400,
            detail="Project folder is not a git repository; run `git init` there first.",
        )

    # Write edits to disk (reusing the same traversal-safe resolver as /edit).
    written: list[str] = []
    for edit in payload.edits:
        try:
            target = _resolve_under_root(project.root_path, edit.path)
        except ValueError as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc
        os.makedirs(os.path.dirname(target), exist_ok=True)
        with open(target, "w", encoding="utf-8") as fh:
            fh.write(edit.content)
        written.append(edit.path.lstrip("/\\"))

    commit_message = payload.commit_message or payload.title
    try:
        result = commit_edits(
            project.root_path,
            branch=payload.branch,
            commit_message=commit_message,
            rel_paths=written,
        )
    except GitError as exc:
        raise HTTPException(status_code=400, detail=f"Git operation failed: {exc}") from exc

    description = ""
    provider_name: str | None = None
    model_name: str | None = None
    if payload.generate_description:
        prompt = (
            "Generate a concise pull request description.\n"
            f"Title: {payload.title}\n"
            f"Goal: {payload.summary_goal}\n"
            f"Files changed: {', '.join(result.files_changed) or 'none'}\n\n"
            "Return a summary, motivation, implementation details, and testing notes.\n\n"
            f"Diff:\n{result.diff[:8000]}"
        )
        try:
            chat = run_chat(prompt, model_ref=payload.model, context=None)
            description = chat.reply
            provider_name = chat.provider
            model_name = chat.model
        except Exception as exc:  # noqa: BLE001 - description is best-effort
            description = f"(LLM description unavailable: {exc})"

    return PullRequestCommitResponse(
        project_id=project_id,
        branch=result.branch,
        base_branch=result.base_branch,
        commit=result.commit,
        files_changed=result.files_changed,
        diff=result.diff,
        description=description,
        provider=provider_name,
        model=model_name,
    )
