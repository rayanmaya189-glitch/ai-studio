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
        # If we were constructed with an explicit curated model list, use it.
        if self._models:
            return self._models

        # Dynamic model listing for OpenRouter.
        # The UI expects "first free/cheapest" models, so we request models
        # sorted by ascending pricing and return the first page.
        #
        # Response is handled defensively since OpenRouter may evolve its
        # schema; we try common keys: id/name/model.
        if self.name == "openrouter":
            try:
                params = {
                    "sort": "pricing-low-to-high",
                    "limit": "10",
                }
                resp = httpx.get(
                    f"{self.base_url}/models",
                    headers=self._headers(),
                    params=params,
                    timeout=self._timeout,
                )
                resp.raise_for_status()
                payload = resp.json()
                items = payload.get("data") if isinstance(payload, dict) else None
                if not isinstance(items, list):
                    return []

                out: list[str] = []
                for m in items:
                    if not isinstance(m, dict):
                        continue
                    model_id = m.get("id") or m.get("name") or m.get("model")
                    if isinstance(model_id, str) and model_id:
                        out.append(model_id)

                return out
            except Exception:
                # UI should not break if model listing fails; provider will
                # still be usable for chat with a configured model.
                return []

        return []

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
