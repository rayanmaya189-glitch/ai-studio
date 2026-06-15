"""Provider registry: builds providers from config and resolves models.

Model references everywhere in the app use the form ``"<provider>:<model>"``
(e.g. ``ollama:qwen2.5-coder``, ``anthropic:claude-opus-4-8``). The registry
always includes the `stub` provider so the app is functional with no keys set.
"""

from __future__ import annotations

from functools import lru_cache

from app.config import settings
from app.providers.anthropic import AnthropicProvider
from app.providers.base import LLMProvider
from app.providers.ollama import OllamaProvider
from app.providers.openai_compat import OpenAICompatProvider
from app.providers.stub import StubProvider

# Curated default model lists for key-based providers (the live list is not
# always enumerable without extra calls; these give the UI something to show).
_OPENAI_MODELS = ["gpt-4o", "gpt-4o-mini", "text-embedding-3-small"]
_OPENROUTER_MODELS = ["openai/gpt-4o", "anthropic/claude-3.5-sonnet", "meta-llama/llama-3.1-8b-instruct"]
_NIM_MODELS = ["meta/llama-3.1-8b-instruct", "nvidia/nv-embed-v1"]
_ANTHROPIC_MODELS = ["claude-opus-4-8", "claude-sonnet-4-6", "claude-haiku-4-5-20251001"]


class ProviderRegistry:
    def __init__(self) -> None:
        self._providers: dict[str, LLMProvider] = {}
        self._build()

    def _build(self) -> None:
        # stub is always present.
        self._register(StubProvider())

        self._register(OllamaProvider(settings.ollama_base_url))

        self._register(
            OpenAICompatProvider(
                "openai", settings.openai_base_url, settings.openai_api_key, _OPENAI_MODELS
            )
        )
        self._register(
            OpenAICompatProvider(
                "openrouter",
                settings.openrouter_base_url,
                settings.openrouter_api_key,
                _OPENROUTER_MODELS,
            )
        )
        self._register(
            OpenAICompatProvider("nim", settings.nim_base_url, settings.nim_api_key, _NIM_MODELS)
        )
        self._register(
            AnthropicProvider(
                settings.anthropic_base_url, settings.anthropic_api_key, _ANTHROPIC_MODELS
            )
        )

    def _register(self, provider: LLMProvider) -> None:
        self._providers[provider.name] = provider

    def all(self) -> list[LLMProvider]:
        return list(self._providers.values())

    def get(self, name: str) -> LLMProvider:
        if name not in self._providers:
            raise KeyError(f"Unknown provider: {name!r}")
        return self._providers[name]

    def resolve(self, ref: str | None) -> tuple[LLMProvider, str]:
        """Resolve a "<provider>:<model>" ref to (provider, model).

        Falls back to the configured default, and finally to the stub provider
        if the requested provider exists but isn't available (no creds / daemon
        down), so callers always get a usable provider.
        """
        ref = ref or settings.default_chat_model
        provider_name, _, model = ref.partition(":")
        if not model:
            provider_name, model = "stub", "echo"

        provider = self._providers.get(provider_name)
        if provider is None or not provider.available():
            return self._providers["stub"], "echo"
        return provider, model


@lru_cache
def get_registry() -> ProviderRegistry:
    return ProviderRegistry()
