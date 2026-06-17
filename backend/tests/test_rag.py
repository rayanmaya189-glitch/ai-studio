"""RAG pipeline tests: chunking, local vector store, ingest + retrieve.

Embedding quality isn't asserted (the stub provider's vectors are hash-based and
non-semantic); these tests pin the *plumbing* — chunk boundaries, storage,
scored retrieval, project isolation, and re-ingest replacement.
"""

from __future__ import annotations

from app.providers.registry import get_registry
from app.providers.base import LLMProvider, ChatMessage
from app.rag.chunking import chunk_document
from app.rag.ingest import ingest_project, retrieve
from app.rag.vector_store import LocalStore


class _RagTestProvider(LLMProvider):
    """Local test provider for RAG tests that create their own provider context."""
    name = "test"
    def available(self) -> bool:
        return True
    def list_models(self) -> list[str]:
        return ["test-model"]
    def chat(self, messages: list[ChatMessage], model: str) -> str:
        return "ok"
    def embed(self, texts: list[str], model: str) -> list[list[float]]:
        return [[0.0] * 64 for _ in texts]


def _ensure_test_provider():
    reg = get_registry()
    if "test" not in {p.name for p in reg.all()}:
        reg._register(_RagTestProvider())


def test_chunk_code_carries_symbols(tmp_path):
    # Bodies padded so the file comfortably exceeds the ~1.2k-char chunk size
    # and the structure-aware chunker splits it into multiple chunks.
    body = "\n".join(f"    x = x + {j}  # step {j}" for j in range(8))
    code = "\n".join(f"def f_{i}(x):\n{body}\n    return x\n" for i in range(20))
    chunks = chunk_document("mod.py", code)
    assert len(chunks) >= 2  # split into multiple semantic chunks
    # At least one chunk should report the function symbols it defines.
    assert any(c.symbols for c in chunks)
    # Indices are contiguous from 0.
    assert [c.index for c in chunks] == list(range(len(chunks)))


def test_chunk_plain_text_fallback():
    text = "para one. " * 400  # ~4000 chars, no parseable language
    chunks = chunk_document("README.md", text)
    assert len(chunks) >= 2
    assert all(c.text.strip() for c in chunks)


def test_chunk_empty_document_yields_nothing():
    assert chunk_document("a.py", "   \n  ") == []


def test_local_store_search_orders_by_similarity(tmp_path):
    store = LocalStore(str(tmp_path))
    store.upsert(
        "p1",
        [[1.0, 0.0], [0.0, 1.0], [0.9, 0.1]],
        [
            {"source_path": "a", "chunk_index": 0, "text": "a"},
            {"source_path": "b", "chunk_index": 0, "text": "b"},
            {"source_path": "c", "chunk_index": 0, "text": "c"},
        ],
    )
    hits = store.search("p1", [1.0, 0.0], limit=2)
    assert len(hits) == 2
    assert hits[0].payload["source_path"] == "a"  # exact match ranks first
    assert hits[0].score >= hits[1].score


def test_local_store_project_isolation_and_delete(tmp_path):
    store = LocalStore(str(tmp_path))
    store.upsert("p1", [[1.0, 0.0]], [{"source_path": "x", "chunk_index": 0, "text": "x"}])
    store.upsert("p2", [[0.0, 1.0]], [{"source_path": "y", "chunk_index": 0, "text": "y"}])
    assert len(store.search("p1", [1.0, 0.0], limit=5)) == 1
    assert store.search("p1", [1.0, 0.0], 5)[0].payload["source_path"] == "x"

    store.delete_project("p1")
    assert store.search("p1", [1.0, 0.0], limit=5) == []
    # p2 untouched.
    assert len(store.search("p2", [0.0, 1.0], limit=5)) == 1


def test_ingest_project_then_retrieve(tmp_path, monkeypatch):
    _ensure_test_provider()
    # Force the local store into an isolated dir regardless of Qdrant presence.
    from app.rag import ingest as ingest_mod

    store = LocalStore(str(tmp_path / "vec"))
    monkeypatch.setattr(ingest_mod, "get_vector_store", lambda: store)

    src = tmp_path / "src"
    src.mkdir()
    (src / "auth.py").write_text(
        "def login(user, pw):\n    '''Authenticate and return a token.'''\n    return True\n"
    )
    (src / "binary.png").write_bytes(b"\x00\x01\x02not text")

    result = ingest_project("proj", str(src), ["auth.py", "binary.png"])
    assert result.files_ingested == 1  # png skipped (not an embed ext)
    assert result.chunks >= 1

    hits = retrieve("proj", "authenticate user login", limit=3)
    assert hits  # retrieval returns something
    assert any(h.source_path == "auth.py" for h in hits)
    assert all(isinstance(h.score, float) for h in hits)


def test_ingest_project_replaces_on_reingest(tmp_path, monkeypatch):
    _ensure_test_provider()
    from app.rag import ingest as ingest_mod

    store = LocalStore(str(tmp_path / "vec"))
    monkeypatch.setattr(ingest_mod, "get_vector_store", lambda: store)

    src = tmp_path / "src"
    src.mkdir()
    (src / "a.py").write_text("def a():\n    return 1\n")
    ingest_project("proj", str(src), ["a.py"])
    first = len(store.search("proj", [0.1] * 64, limit=100))

    # Re-ingest the same file: count must not grow (replace, not append).
    ingest_project("proj", str(src), ["a.py"])
    second = len(store.search("proj", [0.1] * 64, limit=100))
    assert second == first
