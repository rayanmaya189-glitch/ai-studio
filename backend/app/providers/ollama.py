"""Ollama provider (local daemon, no API key required).

Availability is checked by pinging the daemon; if it isn't running the
registry simply omits it from the available set.
"""

from __future__ import annotations

import httpx

from app.providers.base import ChatMessage, LLMProvider


class OllamaProvider(LLMProvider):
    name = "ollama"

    def __init__(self, base_url: str, timeout: float = 120.0) -> None:
        self.base_url = base_url.rstrip("/")
        self._timeout = timeout

    def available(self) -> bool:
        try:
            resp = httpx.get(f"{self.base_url}/api/tags", timeout=2.0)
            return resp.status_code == 200
        except httpx.HTTPError:
            return False

    def list_models(self) -> list[str]:
        try:
            resp = httpx.get(f"{self.base_url}/api/tags", timeout=2.0)
            resp.raise_for_status()
            return [m["name"] for m in resp.json().get("models", [])]
        except httpx.HTTPError:
            return []

    def chat(self, messages: list[ChatMessage], model: str) -> str:
        resp = httpx.post(
            f"{self.base_url}/api/chat",
            json={
                "model": model,
                "messages": [{"role": m.role, "content": m.content} for m in messages],
                "stream": False,
            },
            timeout=self._timeout,
        )
        resp.raise_for_status()
        return resp.json()["message"]["content"]

    def embed(self, texts: list[str], model: str) -> list[list[float]]:
        vectors: list[list[float]] = []
        for text in texts:
            resp = httpx.post(
                f"{self.base_url}/api/embeddings",
                json={"model": model, "prompt": text},
                timeout=self._timeout,
            )
            resp.raise_for_status()
            vectors.append(resp.json()["embedding"])
        return vectors
