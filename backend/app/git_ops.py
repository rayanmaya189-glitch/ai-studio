"""Thin, safe wrapper around the local ``git`` CLI for the PR generator (F13).

Why subprocess + git CLI instead of a library: it adds no dependency, matches
what users already have installed, and keeps the operations transparent. Every
call is scoped to the project's repo via ``-C <root>`` and never touches the
network (no fetch/push) — pushing/opening a hosted PR is a deliberate follow-up
that needs a host token.
"""

from __future__ import annotations

import os
import shutil
import subprocess
from dataclasses import dataclass, field


class GitError(RuntimeError):
    """A git command failed or git is unavailable."""


@dataclass
class CommitResult:
    branch: str
    base_branch: str
    commit: str | None
    files_changed: list[str] = field(default_factory=list)
    diff: str = ""


def _git(root: str, *args: str, check: bool = True) -> subprocess.CompletedProcess:
    if shutil.which("git") is None:
        raise GitError("git is not installed on the server")
    proc = subprocess.run(
        ["git", "-C", root, *args],
        capture_output=True,
        text=True,
        timeout=30,
    )
    if check and proc.returncode != 0:
        raise GitError(proc.stderr.strip() or f"git {' '.join(args)} failed")
    return proc


def is_git_repo(root: str) -> bool:
    if shutil.which("git") is None:
        return False
    proc = _git(root, "rev-parse", "--is-inside-work-tree", check=False)
    return proc.returncode == 0 and proc.stdout.strip() == "true"


def current_branch(root: str) -> str:
    proc = _git(root, "rev-parse", "--abbrev-ref", "HEAD")
    return proc.stdout.strip()


def _sanitize_branch(name: str) -> str:
    safe = "".join(c if (c.isalnum() or c in "-_/.") else "-" for c in name.strip())
    safe = safe.strip("-/") or "ads-change"
    return f"ads/{safe}" if not safe.startswith("ads/") else safe


def commit_edits(
    root: str,
    *,
    branch: str | None,
    commit_message: str,
    rel_paths: list[str],
) -> CommitResult:
    """Create/switch to ``branch``, stage the given paths, commit, return the diff.

    ``rel_paths`` must already be written to disk (the edit-apply step does that).
    The diff returned is the committed change vs the base branch.
    """
    if not is_git_repo(root):
        raise GitError("Project is not a git repository")

    base = current_branch(root)
    target = _sanitize_branch(branch) if branch else _sanitize_branch(commit_message[:40])

    # Create or reuse the branch.
    existing = _git(root, "rev-parse", "--verify", target, check=False)
    if existing.returncode == 0:
        _git(root, "checkout", target)
    else:
        _git(root, "checkout", "-b", target)

    # Stage only the files we touched (keep the user's other changes alone).
    if rel_paths:
        _git(root, "add", "--", *rel_paths)
    else:
        _git(root, "add", "-A")

    # Nothing staged → no commit, but still return a (possibly empty) diff.
    staged = _git(root, "diff", "--cached", "--name-only")
    files_changed = [ln for ln in staged.stdout.splitlines() if ln.strip()]

    commit_sha: str | None = None
    if files_changed:
        env = {
            **os.environ,
            "GIT_AUTHOR_NAME": os.getenv("GIT_AUTHOR_NAME", "ADS Agent"),
            "GIT_AUTHOR_EMAIL": os.getenv("GIT_AUTHOR_EMAIL", "ads@localhost"),
            "GIT_COMMITTER_NAME": os.getenv("GIT_COMMITTER_NAME", "ADS Agent"),
            "GIT_COMMITTER_EMAIL": os.getenv("GIT_COMMITTER_EMAIL", "ads@localhost"),
        }
        proc = subprocess.run(
            ["git", "-C", root, "commit", "-m", commit_message],
            capture_output=True,
            text=True,
            timeout=30,
            env=env,
        )
        if proc.returncode != 0:
            raise GitError(proc.stderr.strip() or "git commit failed")
        commit_sha = _git(root, "rev-parse", "HEAD").stdout.strip()

    # Diff of this branch vs the base it forked from.
    if base and base != target:
        diff = _git(root, "diff", f"{base}...{target}", check=False).stdout
    else:
        diff = _git(root, "show", "--no-color", commit_sha or "HEAD", check=False).stdout

    return CommitResult(
        branch=target,
        base_branch=base,
        commit=commit_sha,
        files_changed=files_changed,
        diff=diff,
    )
