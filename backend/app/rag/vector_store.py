"""Vector store abstraction for RAG (F3).

Two backends behind one interface:

- ``QdrantStore`` — the PRD default; per-project collections, cosine distance,
  built to scale to millions of vectors.
- ``LocalStore`` — a dependency-free on-disk fallback (one JSON file per
  project) with brute-force cosine search, so retrieval works with zero
  external services. Fine for small/demo projects; not for 500k LOC.

``get_vector_store()`` returns Qdrant when the daemon answers, else the local
store, so callers never branch on availability.
"""

from __future__ import annotations

import json
import math
import os
from abc import ABC, abstractmethod
from dataclasses import dataclass

from app.config import settings


@dataclass
class SearchHit:
    score: float
    payload: dict


class VectorStore(ABC):
    backend: str = "base"

    @abstractmethod
    def upsert(self, project_id: str, vectors: list[list[float]], payloads: list[dict]) -> int:
        """Store vectors+payloads for a project; return the count stored."""

    @abstractmethod
    def search(self, project_id: str, query_vector: list[float], limit: int) -> list[SearchHit]:
        """Return the top-``limit`` hits by cosine similarity."""

    @abstractmethod
    def delete_project(self, project_id: str) -> None:
        """Drop all vectors for a project (called before a re-ingest)."""


def _cosine(a: list[float], b: list[float]) -> float:
    dot = sum(x * y for x, y in zip(a, b, strict=False))
    na = math.sqrt(sum(x * x for x in a))
    nb = math.sqrt(sum(y * y for y in b))
    if na == 0 or nb == 0:
        return 0.0
    return dot / (na * nb)


class LocalStore(VectorStore):
    """Brute-force JSON-backed store. Scales poorly by design — it's the
    zero-config fallback, not the production path."""

    backend = "local"

    def __init__(self, root: str) -> None:
        self._root = root
        os.makedirs(root, exist_ok=True)

    def _path(self, project_id: str) -> str:
        return os.path.join(self._root, f"project_{project_id}.json")

    def _load(self, project_id: str) -> list[dict]:
        path = self._path(project_id)
        if not os.path.exists(path):
            return []
        try:
            with open(path, encoding="utf-8") as fh:
                return json.load(fh)
        except (OSError, json.JSONDecodeError):
            return []

    def upsert(self, project_id: str, vectors: list[list[float]], payloads: list[dict]) -> int:
        records = self._load(project_id)
        for vec, payload in zip(vectors, payloads, strict=True):
            records.append({"vector": vec, "payload": payload})
        with open(self._path(project_id), "w", encoding="utf-8") as fh:
            json.dump(records, fh)
        return len(vectors)

    def search(self, project_id: str, query_vector: list[float], limit: int) -> list[SearchHit]:
        records = self._load(project_id)
        scored = [
            SearchHit(score=_cosine(query_vector, r["vector"]), payload=r["payload"])
            for r in records
        ]
        scored.sort(key=lambda h: h.score, reverse=True)
        return scored[:limit]

    def delete_project(self, project_id: str) -> None:
        path = self._path(project_id)
        if os.path.exists(path):
            os.remove(path)


class QdrantStore(VectorStore):
    backend = "qdrant"

    def __init__(self, url: str, timeout: float) -> None:
        from qdrant_client import QdrantClient

        self._client = QdrantClient(url=url, timeout=timeout)

    @staticmethod
    def _collection(project_id: str) -> str:
        return f"project_{project_id}"

    def _ensure_collection(self, project_id: str, dim: int) -> None:
        from qdrant_client.models import Distance, VectorParams

        name = self._collection(project_id)
        existing = {c.name for c in self._client.get_collections().collections}
        if name not in existing:
            self._client.create_collection(
                collection_name=name,
                vectors_config=VectorParams(size=dim, distance=Distance.COSINE),
            )

    def upsert(self, project_id: str, vectors: list[list[float]], payloads: list[dict]) -> int:
        from qdrant_client.models import PointStruct

        if not vectors:
            return 0
        self._ensure_collection(project_id, len(vectors[0]))
        points = [
            PointStruct(
                id=abs(hash((p["source_path"], p["chunk_index"]))) % (10**15),
                vector=vec,
                payload=p,
            )
            for vec, p in zip(vectors, payloads, strict=True)
        ]
        self._client.upsert(collection_name=self._collection(project_id), points=points)
        return len(points)

    def search(self, project_id: str, query_vector: list[float], limit: int) -> list[SearchHit]:
        try:
            res = self._client.query_points(
                collection_name=self._collection(project_id),
                query=query_vector,
                limit=limit,
                with_payload=True,
            ).points
        except Exception:  # noqa: BLE001 - missing collection / empty project
            return []
        return [SearchHit(score=p.score, payload=p.payload or {}) for p in res]

    def delete_project(self, project_id: str) -> None:
        try:
            self._client.delete_collection(self._collection(project_id))
        except Exception:  # noqa: BLE001 - nothing to delete
            pass


def _qdrant_reachable(url: str, timeout: float) -> bool:
    try:
        import httpx

        return httpx.get(url, timeout=timeout).status_code < 500
    except Exception:  # noqa: BLE001 - any failure means "not reachable"
        return False


def get_vector_store() -> VectorStore:
    """Return Qdrant if reachable, else the local on-disk fallback."""
    if _qdrant_reachable(settings.qdrant_url, settings.qdrant_timeout):
        try:
            return QdrantStore(settings.qdrant_url, settings.qdrant_timeout)
        except Exception:  # noqa: BLE001 - client import/init failure
            pass
    return LocalStore(settings.local_vector_path)
