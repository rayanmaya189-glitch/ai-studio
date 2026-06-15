"""OpenAI-compatible provider.

OpenAI, OpenRouter, and NVIDIA NIM all speak the same /chat/completions and
/embeddings wire format, so they share this implementation and differ only by
base URL, API key, and curated model list.
"""

from __future__ import annotations

import httpx

from app.providers.base import ChatMessage, LLMProvider


class OpenAICompatProvider(LLMProvider):
    def __init__(
        self,
        name: str,
        base_url: str,
        api_key: str | None,
        models: list[str],
        timeout: float = 60.0,
    ) -> None:
        self.name = name
        self.base_url = base_url.rstrip("/")
        self.api_key = api_key
        self._models = models
        self._timeout = timeout

    def available(self) -> bool:
        return bool(self.api_key)

    def list_models(self) -> list[str]:
        return self._models

    def _headers(self) -> dict[str, str]:
        return {"Authorization": f"Bearer {self.api_key}", "Content-Type": "application/json"}

    def chat(self, messages: list[ChatMessage], model: str) -> str:
        payload = {
            "model": model,
            "messages": [{"role": m.role, "content": m.content} for m in messages],
        }
        resp = httpx.post(
            f"{self.base_url}/chat/completions",
            headers=self._headers(),
            json=payload,
            timeout=self._timeout,
        )
        resp.raise_for_status()
        return resp.json()["choices"][0]["message"]["content"]

    def embed(self, texts: list[str], model: str) -> list[list[float]]:
        resp = httpx.post(
            f"{self.base_url}/embeddings",
            headers=self._headers(),
            json={"model": model, "input": texts},
            timeout=self._timeout,
        )
        resp.raise_for_status()
        return [item["embedding"] for item in resp.json()["data"]]
