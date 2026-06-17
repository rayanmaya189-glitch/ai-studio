"""Provider registry tests."""

from __future__ import annotations

import pytest
from app.providers.base import LLMProvider, ChatMessage
from app.providers.registry import ProviderRegistry


class TestProvider(LLMProvider):
    """Minimal provider for tests — no network required."""
    name = "test"

    def available(self) -> bool:
        return True

    def list_models(self) -> list[str]:
        return ["test-model"]

    def chat(self, messages: list[ChatMessage], model: str) -> str:
        last = next((m.content for m in reversed(messages) if m.role == "user"), "")
        return f"[test:{model}] Echo: {last}"

    def embed(self, texts: list[str], model: str) -> list[list[float]]:
        return [[0.0] * 64 for _ in texts]


def test_registry_empty_when_no_providers_configured():
    reg = ProviderRegistry()
    # With no DB config rows (test DB is empty), no providers should be registered.
    assert len(reg.all()) == 0


def test_registry_resolve_raises_for_missing_provider():
    reg = ProviderRegistry()
    reg._register(TestProvider())
    with pytest.raises(ValueError, match="not configured or enabled"):
        reg.resolve("nonexistent:model")


def test_resolve_works_with_registered_provider():
    reg = ProviderRegistry()
    reg._register(TestProvider())
    provider, model = reg.resolve("test:test-model")
    assert provider.name == "test"
    assert model == "test-model"


def test_registry_raises_for_invalid_ref_format():
    reg = ProviderRegistry()
    with pytest.raises(ValueError, match="Invalid model reference"):
        reg.resolve("no-colon-here")