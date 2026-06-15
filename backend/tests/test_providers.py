"""Provider registry + stub provider behaviour."""

from __future__ import annotations

from app.providers.base import ChatMessage
from app.providers.registry import ProviderRegistry
from app.providers.stub import StubProvider


def test_stub_always_available_and_echoes():
    stub = StubProvider()
    assert stub.available() is True
    reply = stub.chat([ChatMessage(role="user", content="hello world")], "echo")
    assert "hello world" in reply


def test_stub_embeddings_shape_and_determinism():
    stub = StubProvider()
    a = stub.embed(["abc"], "echo-embed")
    b = stub.embed(["abc"], "echo-embed")
    assert len(a) == 1 and len(a[0]) == 64
    assert a == b  # deterministic


def test_registry_includes_stub_and_resolves_default():
    reg = ProviderRegistry()
    assert "stub" in {p.name for p in reg.all()}
    provider, model = reg.resolve(None)  # falls back to default_chat_model
    assert provider.available()


def test_registry_falls_back_to_stub_for_unconfigured_provider():
    reg = ProviderRegistry()
    # anthropic has no key in the test env -> not available -> stub fallback.
    provider, model = reg.resolve("anthropic:claude-opus-4-8")
    assert provider.name == "stub"
    assert model == "echo"
