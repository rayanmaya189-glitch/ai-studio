"""RAG ingestion + retrieval (F3).

Pipeline: semantic chunking (``chunking.chunk_document``) -> embedding (via the
provider layer, default ``nomic-embed-text`` through Ollama, or the stub vector
with zero config) -> upsert into a per-project vector store (Qdrant, or the
local on-disk fallback). Retrieval embeds the query the same way and returns
scored chunks, which the agent layer threads into prompts as project context.

``ingest_text(project_id, source_path, text)`` keeps its original signature;
``ingest_project`` and ``retrieve`` are the new entry points used by the scan
and chat flows.
"""

from __future__ import annotations

import os
from dataclasses import dataclass, field

from app.config import settings
from app.providers import get_registry
from app.rag.chunking import chunk_document
from app.rag.vector_store import get_vector_store

# Skip embedding files larger than this (generated/minified blobs hurt quality
# and cost; the scanner already capped parsing similarly).
_MAX_EMBED_BYTES = 500_000
# Extensions worth embedding for retrieval: code plus docs/specs/infra text.
_EMBED_EXTS = {
    ".py",
    ".java",
    ".go",
    ".ts",
    ".tsx",
    ".js",
    ".jsx",
    ".cs",
    ".rs",
    ".md",
    ".rst",
    ".txt",
    ".json",
    ".yaml",
    ".yml",
    ".toml",
    ".env",
    ".sql",
    ".proto",
    ".dockerfile",
}


@dataclass
class IngestResult:
    chunks: int
    embedded: bool
    stored: bool
    backend: str
    note: str
    # Kept for backwards-compat with the original field name.
    stored_in_qdrant: bool = False


@dataclass
class ProjectIngestResult:
    files_ingested: int
    chunks: int
    backend: str
    embedded: bool
    note: str
    skipped: int = 0


@dataclass
class RetrievedChunk:
    text: str
    source_path: str
    score: float
    start_line: int = 0
    end_line: int = 0
    symbols: list[str] = field(default_factory=list)


def _embed(texts: list[str]) -> tuple[list[list[float]], bool, str]:
    """Embed ``texts`` via the configured embed model; (vectors, ok, model)."""
    registry = get_registry()
    provider, model = registry.resolve(settings.default_embed_model)
    try:
        return provider.embed(texts, model), True, f"{provider.name}:{model}"
    except Exception:  # noqa: BLE001 - degrade gracefully if embedding fails
        return [], False, f"{provider.name}:{model}"


def ingest_text(project_id: str, source_path: str, text: str) -> IngestResult:
    """Chunk, embed, and store one document's text."""
    chunks = chunk_document(source_path, text)
    if not chunks:
        return IngestResult(
            chunks=0,
            embedded=False,
            stored=False,
            backend="none",
            note="empty document",
        )

    vectors, embedded, _ = _embed([c.text for c in chunks])
    if not embedded:
        return IngestResult(
            chunks=len(chunks),
            embedded=False,
            stored=False,
            backend="none",
            note="embedding unavailable; nothing stored",
        )

    store = get_vector_store()
    payloads = [c.to_payload(source_path) for c in chunks]
    stored_count = store.upsert(project_id, vectors, payloads)
    stored = stored_count > 0
    return IngestResult(
        chunks=len(chunks),
        embedded=True,
        stored=stored,
        backend=store.backend,
        stored_in_qdrant=stored and store.backend == "qdrant",
        note=f"ingested {stored_count} chunks into {store.backend}",
    )


def _should_embed(rel_path: str) -> bool:
    base = os.path.basename(rel_path).lower()
    if base in {"dockerfile", ".env", ".env.example"}:
        return True
    return os.path.splitext(rel_path)[1].lower() in _EMBED_EXTS


def ingest_project(project_id: str, root_path: str, rel_paths: list[str]) -> ProjectIngestResult:
    """Ingest a set of project files (relative to ``root_path``) into the store.

    Clears the project's existing vectors first so a re-scan replaces rather
    than duplicates. Embeds in one batch per file; files that can't be read or
    embedded are skipped rather than aborting the run.
    """
    store = get_vector_store()
    store.delete_project(project_id)

    all_vectors: list[list[float]] = []
    all_payloads: list[dict] = []
    files_ingested = 0
    skipped = 0
    any_embedded = False

    for rel in rel_paths:
        if not _should_embed(rel):
            skipped += 1
            continue
        full = os.path.join(root_path, rel)
        try:
            size = os.path.getsize(full)
            if size > _MAX_EMBED_BYTES:
                skipped += 1
                continue
            with open(full, "rb") as fh:
                raw = fh.read()
            if b"\x00" in raw[:1024]:  # binary
                skipped += 1
                continue
            text = raw.decode("utf-8", errors="replace")
        except OSError:
            skipped += 1
            continue

        chunks = chunk_document(rel, text)
        if not chunks:
            skipped += 1
            continue
        vectors, embedded, _ = _embed([c.text for c in chunks])
        if not embedded:
            skipped += 1
            continue
        any_embedded = True
        all_vectors.extend(vectors)
        all_payloads.extend(c.to_payload(rel) for c in chunks)
        files_ingested += 1

    stored = store.upsert(project_id, all_vectors, all_payloads) if all_vectors else 0
    return ProjectIngestResult(
        files_ingested=files_ingested,
        chunks=stored,
        backend=store.backend,
        embedded=any_embedded,
        skipped=skipped,
        note=f"ingested {files_ingested} files / {stored} chunks into {store.backend}",
    )


def retrieve(project_id: str, query: str, limit: int = 5) -> list[RetrievedChunk]:
    """Embed ``query`` and return the top-``limit`` matching chunks."""
    vectors, embedded, _ = _embed([query])
    if not embedded or not vectors:
        return []
    hits = get_vector_store().search(project_id, vectors[0], limit)
    out: list[RetrievedChunk] = []
    for hit in hits:
        p = hit.payload or {}
        out.append(
            RetrievedChunk(
                text=p.get("text", ""),
                source_path=p.get("source_path", "?"),
                score=hit.score,
                start_line=p.get("start_line", 0),
                end_line=p.get("end_line", 0),
                symbols=p.get("symbols", []),
            )
        )
    return out


def build_context_block(chunks: list[RetrievedChunk], max_chars: int = 6_000) -> str:
    """Render retrieved chunks into a prompt-ready context block."""
    if not chunks:
        return ""
    parts: list[str] = []
    used = 0
    for c in chunks:
        loc = f"{c.source_path}:{c.start_line + 1}-{c.end_line + 1}"
        block = f"--- {loc} ---\n{c.text}\n"
        if used + len(block) > max_chars:
            break
        parts.append(block)
        used += len(block)
    return "\n".join(parts)
