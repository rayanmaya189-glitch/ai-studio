"""Anthropic / Claude provider.

Uses the Messages API directly over HTTP. Anthropic does not offer an
embeddings endpoint, so embed() raises — pair Claude (chat) with another
provider (Ollama, OpenAI) for embeddings.
"""

from __future__ import annotations

import httpx

from app.providers.base import ChatMessage, LLMProvider

_ANTHROPIC_VERSION = "2023-06-01"
_DEFAULT_MAX_TOKENS = 2048


class AnthropicProvider(LLMProvider):
    name = "anthropic"

    def __init__(
        self, base_url: str, api_key: str | None, models: list[str], timeout: float = 60.0
    ) -> None:
        self.base_url = base_url.rstrip("/")
        self.api_key = api_key
        self._models = models
        self._timeout = timeout

    def available(self) -> bool:
        return bool(self.api_key)

    def list_models(self) -> list[str]:
        return self._models

    def chat(self, messages: list[ChatMessage], model: str) -> str:
        # Anthropic takes the system prompt as a top-level field, not a message.
        system = "\n".join(m.content for m in messages if m.role == "system")
        turns = [
            {"role": m.role, "content": m.content}
            for m in messages
            if m.role in ("user", "assistant")
        ]
        payload: dict = {"model": model, "max_tokens": _DEFAULT_MAX_TOKENS, "messages": turns}
        if system:
            payload["system"] = system

        resp = httpx.post(
            f"{self.base_url}/v1/messages",
            headers={
                "x-api-key": self.api_key or "",
                "anthropic-version": _ANTHROPIC_VERSION,
                "content-type": "application/json",
            },
            json=payload,
            timeout=self._timeout,
        )
        resp.raise_for_status()
        blocks = resp.json().get("content", [])
        return "".join(b.get("text", "") for b in blocks if b.get("type") == "text")

    def embed(self, texts: list[str], model: str) -> list[list[float]]:
        raise NotImplementedError(
            "Anthropic has no embeddings endpoint; use ollama/openai for embeddings."
        )
