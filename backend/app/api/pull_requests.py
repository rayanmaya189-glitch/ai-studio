"""F13 - Pull request generator (scaffold).

This endpoint generates a PR description using an LLM. For now, it is a
best-effort scaffold that can run with the `stub` provider (zero config).

Later versions can:
- create git commits/branches
- produce file diffs from the edit apply step
- open real PRs via a provider (GitHub/GitLab)
"""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.agents.graph import run_chat
from app.db import get_db
from app.models import Project
from app.schemas import PullRequestGenerateRequest, PullRequestGenerateResponse

router = APIRouter(prefix="/projects", tags=["pull-requests"])


@router.post("/{project_id}/pull-requests/generate", response_model=PullRequestGenerateResponse)
def generate_pr(
    project_id: str,
    payload: PullRequestGenerateRequest,
    db: Session = Depends(get_db),
) -> PullRequestGenerateResponse:
    project = db.get(Project, project_id)
    if project is None:
        raise HTTPException(status_code=404, detail="Project not found")

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
