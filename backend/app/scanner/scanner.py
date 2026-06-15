"""Project scanner (F2).

STUB-level implementation: walks the project folder, classifies files by
extension, and aggregates counts. The real version will use Tree-sitter to
parse symbols and detect frameworks/services/APIs — that work plugs in behind
the same ``scan_project`` signature and ``ScanMetadata`` shape.
"""

from __future__ import annotations

import os
from dataclasses import dataclass, field

# Extension -> language. Mirrors the PRD's supported language set.
_EXT_LANG = {
    ".py": "Python",
    ".java": "Java",
    ".go": "Go",
    ".ts": "TypeScript",
    ".tsx": "TypeScript",
    ".js": "JavaScript",
    ".jsx": "JavaScript",
    ".cs": "C#",
    ".rs": "Rust",
}

_IGNORE_DIRS = {".git", "node_modules", ".venv", "venv", "__pycache__", ".next", "dist", "build"}


@dataclass
class ScanMetadata:
    file_count: int = 0
    total_bytes: int = 0
    languages: dict[str, int] = field(default_factory=dict)
    files: list[dict] = field(default_factory=list)

    def to_dict(self) -> dict:
        return {
            "file_count": self.file_count,
            "total_bytes": self.total_bytes,
            "languages": self.languages,
            # Counts the PRD dashboard expects; real values land with Tree-sitter.
            "service_count": 0,
            "database_count": 0,
            "endpoint_count": 0,
            "note": "stub scanner: file/language counts only; no symbol parsing yet",
        }


def scan_project(root_path: str, max_files: int = 50_000) -> ScanMetadata:
    """Walk ``root_path`` and return aggregate metadata."""
    meta = ScanMetadata()
    if not os.path.isdir(root_path):
        raise FileNotFoundError(f"Project path does not exist: {root_path}")

    for dirpath, dirnames, filenames in os.walk(root_path):
        dirnames[:] = [d for d in dirnames if d not in _IGNORE_DIRS]
        for fname in filenames:
            if meta.file_count >= max_files:
                return meta
            ext = os.path.splitext(fname)[1].lower()
            lang = _EXT_LANG.get(ext)
            full = os.path.join(dirpath, fname)
            try:
                size = os.path.getsize(full)
            except OSError:
                size = 0
            meta.file_count += 1
            meta.total_bytes += size
            if lang:
                meta.languages[lang] = meta.languages.get(lang, 0) + 1
            if len(meta.files) < 5_000:  # cap stored rows for the scaffold
                meta.files.append(
                    {"path": os.path.relpath(full, root_path), "language": lang, "size": size}
                )
    return meta
