"""Language detection and parser-capability tables for the scanner (F2).

Centralises the mapping between file extensions and the PRD's seven supported
languages, plus the directories we never descend into. Kept separate from
``scanner.py`` so the RAG ingester can reuse the same detection.
"""

from __future__ import annotations

import os

# Extension -> language label shown in metadata. Covers the PRD's seven
# languages (Python, Java, Go, TS/JS, C#, Rust) plus a few text formats we
# still want to embed for RAG even though we don't parse them structurally.
EXT_LANG: dict[str, str] = {
    ".py": "Python",
    ".java": "Java",
    ".go": "Go",
    ".ts": "TypeScript",
    ".tsx": "TypeScript",
    ".js": "JavaScript",
    ".jsx": "JavaScript",
    ".cs": "C#",
    ".rs": "Rust",
    ".md": "Markdown",
    ".rst": "reStructuredText",
    ".json": "JSON",
    ".yaml": "YAML",
    ".yml": "YAML",
    ".toml": "TOML",
}

# Language label -> the language id understood by tree_sitter_language_pack's
# ``process()``. Only the structurally-parseable languages appear here; files
# whose language is absent are counted but not symbol-parsed.
PARSE_LANG: dict[str, str] = {
    "Python": "python",
    "Java": "java",
    "Go": "go",
    "TypeScript": "typescript",  # .tsx is special-cased in language_for_path
    "JavaScript": "javascript",
    "C#": "csharp",
    "Rust": "rust",
}

IGNORE_DIRS: frozenset[str] = frozenset(
    {
        ".git",
        "node_modules",
        ".venv",
        "venv",
        "__pycache__",
        ".next",
        "dist",
        "build",
        "target",  # rust/java
        "bin",
        "obj",  # c#
        ".mypy_cache",
        ".pytest_cache",
        ".ruff_cache",
        ".idea",
        ".vscode",
    }
)


def language_for_path(path: str) -> str | None:
    """Return the display language for ``path`` or ``None`` if unknown."""
    return EXT_LANG.get(os.path.splitext(path)[1].lower())


def parse_id_for_path(path: str) -> str | None:
    """Return the ``process()`` language id for ``path`` or ``None``.

    ``.tsx`` maps to the dedicated ``tsx`` grammar; everything else goes
    through ``PARSE_LANG``.
    """
    ext = os.path.splitext(path)[1].lower()
    if ext == ".tsx":
        return "tsx"
    lang = EXT_LANG.get(ext)
    return PARSE_LANG.get(lang) if lang else None
