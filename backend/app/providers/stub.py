"""Zero-dependency provider used when no real credentials are configured.

Replies are deterministic so tests and demos are reproducible. Embeddings are a
cheap hash-based vector — meaningless for retrieval quality, but correctly
shaped so the RAG plumbing can be exercised end-to-end.
"""

from __future__ import annotations

import hashlib

from app.providers.base import ChatMessage, LLMProvider

_EMBED_DIM = 64


class StubProvider(LLMProvider):
    name = "stub"

    def available(self) -> bool:
        return True

    def list_models(self) -> list[str]:
        return ["echo", "echo-embed"]

    def chat(self, messages: list[ChatMessage], model: str) -> str:
        last_user = next(
            (m.content for m in reversed(messages) if m.role == "user"), ""
        )
        return (
            "[stub] No LLM provider is configured, so this is a canned reply. "
            f'You said: "{last_user}". Set a provider key in .env to get real '
            "completions."
        )

    def embed(self, texts: list[str], model: str) -> list[list[float]]:
        vectors: list[list[float]] = []
        for text in texts:
            digest = hashlib.sha256(text.encode("utf-8")).digest()
            # Tile the 32-byte digest up to the embedding dim, normalised to [0,1).
            vec = [digest[i % len(digest)] / 255.0 for i in range(_EMBED_DIM)]
            vectors.append(vec)
        return vectors
