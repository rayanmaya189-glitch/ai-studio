"""RAG ingestion + retrieval (F3).

STUB-level: the embedding call is real (it goes through the provider layer), but
chunking is naive (whole-file / fixed-size) and Qdrant upsert is best-effort —
if Qdrant is unreachable we skip it rather than failing the request. The real
version adds semantic chunking, per-project collections, and retrieval scoring.
"""

from __future__ import annotations

from dataclasses import dataclass

from app.config import settings
from app.providers import get_registry

_CHUNK_CHARS = 1_000


@dataclass
class IngestResult:
    chunks: int
    embedded: bool
    stored_in_qdrant: bool
    note: str


def _chunk(text: str, size: int = _CHUNK_CHARS) -> list[str]:
    return [text[i : i + size] for i in range(0, len(text), size)] or [""]


def ingest_text(project_id: str, source_path: str, text: str) -> IngestResult:
    """Chunk, embed, and (best-effort) upsert one document's text."""
    chunks = _chunk(text)
    registry = get_registry()
    provider, model = registry.resolve(settings.default_embed_model)

    try:
        vectors = provider.embed(chunks, model)
        embedded = True
    except (NotImplementedError, Exception):  # noqa: BLE001 - degrade gracefully in scaffold
        vectors = []
        embedded = False

    stored = _try_upsert_qdrant(project_id, source_path, chunks, vectors) if embedded else False

    return IngestResult(
        chunks=len(chunks),
        embedded=embedded,
        stored_in_qdrant=stored,
        note="stub ingest: naive fixed-size chunking, best-effort Qdrant upsert",
    )


def _try_upsert_qdrant(
    project_id: str, source_path: str, chunks: list[str], vectors: list[list[float]]
) -> bool:
    """Upsert into a per-project Qdrant collection; swallow connection errors."""
    try:
        from qdrant_client import QdrantClient
        from qdrant_client.models import Distance, PointStruct, VectorParams

        client = QdrantClient(url=settings.qdrant_url, timeout=2.0)
        collection = f"project_{project_id}"
        dim = len(vectors[0])
        existing = {c.name for c in client.get_collections().collections}
        if collection not in existing:
            client.create_collection(
                collection_name=collection,
                vectors_config=VectorParams(size=dim, distance=Distance.COSINE),
            )
        points = [
            PointStruct(
                id=abs(hash((source_path, i))) % (10**12),
                vector=vec,
                payload={"source_path": source_path, "chunk_index": i, "text": chunk},
            )
            for i, (chunk, vec) in enumerate(zip(chunks, vectors, strict=True))
        ]
        client.upsert(collection_name=collection, points=points)
        return True
    except Exception:  # noqa: BLE001 - Qdrant optional in scaffold
        return False
