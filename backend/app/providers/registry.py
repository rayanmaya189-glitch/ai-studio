"""Provider registry: builds providers from config and resolves models.

Model references everywhere in the app use the form ``"<provider>:<model>"``
(e.g. ``ollama:qwen2.5-coder``, ``anthropic:claude-opus-4-8``). The registry
only registers providers that have been enabled via the LLM Config UI.
No stub or fake providers are registered.
"""

from __future__ import annotations

from functools import lru_cache

from sqlalchemy import select

from app.config import settings
from app.db import SessionLocal
from app.models import LLMProviderConfig
from app.providers.anthropic import AnthropicProvider
from app.providers.base import LLMProvider
from app.providers.ollama import OllamaProvider
from app.providers.openai_compat import OpenAICompatProvider

# Curated default model lists for key-based providers (the live list is not
# always enumerable without extra calls; these give the UI something to show).
_OPENAI_MODELS = ["gpt-4o", "gpt-4o-mini", "text-embedding-3-small"]
_OPENROUTER_MODELS: list[str] = []
_NIM_MODELS = ["meta/llama-3.1-8b-instruct", "nvidia/nv-embed-v1"]
_ANTHROPIC_MODELS = ["claude-opus-4-8", "claude-sonnet-4-6", "claude-haiku-4-5-20251001"]


class ProviderRegistry:
    def __init__(self) -> None:
        self._providers: dict[str, LLMProvider] = {}
        self._build()

    def _load_db_configs(self) -> dict[str, LLMProviderConfig]:
        with SessionLocal() as db:
            rows = db.scalars(select(LLMProviderConfig)).all()
        return {r.provider_name: r for r in rows}

    def _build(self) -> None:
        db_cfg = self._load_db_configs()

        # Ollama: only register if explicitly enabled via DB config.
        ollama_cfg = db_cfg.get("ollama")
        if ollama_cfg is not None and ollama_cfg.enabled:
            mode = ollama_cfg.ollama_mode or "localhost"
            if mode == "cloud":
                base_url = ollama_cfg.ollama_cloud_base_url or settings.ollama_base_url
            else:
                base_url = ollama_cfg.ollama_local_base_url or settings.ollama_base_url
            self._register(OllamaProvider(base_url))

        # OpenAI compat providers: only register if explicitly enabled.
        for provider_name, default_base, default_key, models in (
            ("openai", settings.openai_base_url, settings.openai_api_key, _OPENAI_MODELS),
            (
                "openrouter",
                settings.openrouter_base_url,
                settings.openrouter_api_key,
                _OPENROUTER_MODELS,
            ),
            ("nim", settings.nim_base_url, settings.nim_api_key, _NIM_MODELS),
        ):
            cfg = db_cfg.get(provider_name)
            if cfg is None or not cfg.enabled:
                continue

            base_url = cfg.base_url or default_base
            api_key = cfg.api_key or default_key
            self._register(OpenAICompatProvider(provider_name, base_url, api_key, models))

        # Anthropic: only register if explicitly enabled.
        anthropic_cfg = db_cfg.get("anthropic")
        if anthropic_cfg is not None and anthropic_cfg.enabled:
            base_url = anthropic_cfg.base_url or settings.anthropic_base_url
            api_key = anthropic_cfg.api_key or settings.anthropic_api_key
            self._register(AnthropicProvider(base_url, api_key, _ANTHROPIC_MODELS))

    def _register(self, provider: LLMProvider) -> None:
        self._providers[provider.name] = provider

    def all(self) -> list[LLMProvider]:
        """Return all registered (real) providers."""
        return list(self._providers.values())

    def get(self, name: str) -> LLMProvider:
        if name not in self._providers:
            raise KeyError(f"Unknown provider: {name!r}")
        return self._providers[name]

    def resolve(self, ref: str | None) -> tuple[LLMProvider, str]:
        """Resolve a "<provider>:<model>" ref to (provider, model).

        If no ref is given, falls back to the configured default chat model.
        Raises ``ValueError`` if no provider can be resolved (no real providers
        configured).
        """
        ref = ref or settings.default_chat_model
        if not ref:
            raise ValueError(
                "No LLM provider configured. "
                "Go to the LLM Config page to enable and configure a provider "
                "(e.g. Ollama, OpenAI, Anthropic, OpenRouter, or NVIDIA NIM)."
            )

        provider_name, _, model = ref.partition(":")
        if not model:
            raise ValueError(
                f"Invalid model reference: {ref!r}. "
                "Expected format '<provider>:<model>' (e.g. 'ollama:qwen2.5-coder')."
            )

        provider = self._providers.get(provider_name)
        if provider is None:
            raise ValueError(
                f"Provider {provider_name!r} is not configured or enabled. "
                "Enable it in the LLM Config page first."
            )
        if not provider.available():
            raise ValueError(
                f"Provider {provider_name!r} is enabled but not available. "
                "Check its credentials and endpoint in the LLM Config page."
            )
        return provider, model


@lru_cache
def get_registry() -> ProviderRegistry:
    return ProviderRegistry()


def reset_registry() -> None:
    """Drop the cached registry so the next ``get_registry()`` rebuilds it.

    Provider instances are constructed from the persisted ``LLMProviderConfig``
    rows at build time, so config changes (enable/disable, new key, new base
    URL) only take effect once the registry is rebuilt. Callers that mutate the
    config (PUT /llm-config) invoke this so changes apply live, without a
    server restart.
    """
    get_registry.cache_clear()