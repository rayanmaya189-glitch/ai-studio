"""Semantic chunking for RAG ingestion (F3).

Code files are chunked with ``tree_sitter_language_pack``'s structure-aware
chunker so a chunk lands on function/class boundaries and carries the symbols it
defines. Non-code text (Markdown, configs) and parse failures fall back to a
paragraph-aware fixed-size splitter. Either way the output is a list of
``Chunk`` with text + retrieval-friendly metadata.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from app.scanner.languages import parse_id_for_path

# Target chunk size in characters. Tuned for code: large enough to hold a small
# function with context, small enough that retrieval stays focused.
_CHUNK_CHARS = 1_200
_OVERLAP_CHARS = 150


@dataclass
class Chunk:
    text: str
    index: int
    start_line: int = 0
    end_line: int = 0
    symbols: list[str] = field(default_factory=list)
    context_path: list[str] = field(default_factory=list)

    def to_payload(self, source_path: str) -> dict:
        return {
            "source_path": source_path,
            "chunk_index": self.index,
            "text": self.text,
            "start_line": self.start_line,
            "end_line": self.end_line,
            "symbols": self.symbols,
            "context_path": self.context_path,
        }


def _fallback_chunks(text: str) -> list[Chunk]:
    """Fixed-size splitter with overlap, used for non-code or unparseable text."""
    if not text.strip():
        return []
    chunks: list[Chunk] = []
    step = max(1, _CHUNK_CHARS - _OVERLAP_CHARS)
    idx = 0
    for start in range(0, len(text), step):
        piece = text[start : start + _CHUNK_CHARS]
        if not piece.strip():
            continue
        # Approximate line numbers from the character offset.
        start_line = text.count("\n", 0, start)
        end_line = start_line + piece.count("\n")
        chunks.append(Chunk(text=piece, index=idx, start_line=start_line, end_line=end_line))
        idx += 1
        if start + _CHUNK_CHARS >= len(text):
            break
    return chunks


def chunk_document(source_path: str, text: str) -> list[Chunk]:
    """Split ``text`` into retrieval chunks, semantically when possible."""
    if not text.strip():
        return []

    parse_id = parse_id_for_path(source_path)
    if parse_id is None:
        return _fallback_chunks(text)

    try:
        from tree_sitter_language_pack import ProcessConfig, process

        result = process(
            text,
            ProcessConfig(language=parse_id, chunk_max_size=_CHUNK_CHARS),
        )
    except Exception:  # noqa: BLE001 - any parse failure -> fixed-size fallback
        return _fallback_chunks(text)

    raw_chunks = list(result.chunks)
    if not raw_chunks:
        return _fallback_chunks(text)

    chunks: list[Chunk] = []
    for i, rc in enumerate(raw_chunks):
        if not rc.content.strip():
            continue
        meta = rc.metadata
        chunks.append(
            Chunk(
                text=rc.content,
                index=i,
                start_line=rc.start_line,
                end_line=rc.end_line,
                symbols=list(getattr(meta, "symbols_defined", []) or []),
                context_path=list(getattr(meta, "context_path", []) or []),
            )
        )
    return chunks or _fallback_chunks(text)
