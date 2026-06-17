"""DB-backed LLM provider configuration: persistence, key masking, live refresh."""

from __future__ import annotations

import pytest
from sqlalchemy import delete

from app.db import SessionLocal
from app.models import LLMProviderConfig
from app.providers import reset_registry


@pytest.fixture(autouse=True)
def _clean_config():
    # The test DB is session-scoped and shared, so provider config written here
    # would otherwise leak into other test modules (e.g. test_providers asserts
    # anthropic has no stored key). Wipe rows and the cached registry around
    # each test for full isolation.
    def _wipe() -> None:
        with SessionLocal() as db:
            db.execute(delete(LLMProviderConfig))
            db.commit()
        reset_registry()

    _wipe()
    yield
    _wipe()


def test_get_returns_all_known_providers_disabled_by_default(client):
    body = client.get("/llm-config").json()
    names = {p["provider_name"] for p in body["providers"]}
    assert names == {"openrouter", "openai", "nim", "ollama", "anthropic"}
    assert all(p["enabled"] is False for p in body["providers"])
    assert all(p["has_api_key"] is False for p in body["providers"])


def test_put_persists_and_masks_api_key(client):
    resp = client.put(
        "/llm-config",
        json={
            "providers": [
                {
                    "provider_name": "openai",
                    "enabled": True,
                    "api_key": "sk-secret-value",
                    "base_url": "https://api.openai.com/v1",
                }
            ]
        },
    )
    assert resp.status_code == 200
    body = resp.json()
    openai = next(p for p in body["providers"] if p["provider_name"] == "openai")
    assert openai["enabled"] is True
    assert openai["has_api_key"] is True
    # The real key is never echoed back to the client.
    assert "api_key" not in openai

    # Persisted: a fresh GET still reports the key is stored.
    again = client.get("/llm-config").json()
    openai2 = next(p for p in again["providers"] if p["provider_name"] == "openai")
    assert openai2["enabled"] is True
    assert openai2["has_api_key"] is True


def test_put_with_null_api_key_preserves_existing_key(client):
    client.put(
        "/llm-config",
        json={"providers": [{"provider_name": "openai", "enabled": True, "api_key": "sk-keep-me"}]},
    )
    # Save again without resending the key (UI sends null when not retyped).
    client.put(
        "/llm-config",
        json={"providers": [{"provider_name": "openai", "enabled": True, "api_key": None}]},
    )
    body = client.get("/llm-config").json()
    openai = next(p for p in body["providers"] if p["provider_name"] == "openai")
    assert openai["has_api_key"] is True


def test_put_with_empty_string_api_key_clears_key(client):
    client.put(
        "/llm-config",
        json={
            "providers": [{"provider_name": "openai", "enabled": True, "api_key": "sk-clear-me"}]
        },
    )
    client.put(
        "/llm-config",
        json={"providers": [{"provider_name": "openai", "enabled": False, "api_key": ""}]},
    )
    body = client.get("/llm-config").json()
    openai = next(p for p in body["providers"] if p["provider_name"] == "openai")
    assert openai["has_api_key"] is False


def test_enabling_provider_makes_it_appear_in_providers_live(client):
    # Not present before configuration (only stub is always available).
    before = {p["name"] for p in client.get("/providers").json()}
    assert "anthropic" not in before

    client.put(
        "/llm-config",
        json={
            "providers": [{"provider_name": "anthropic", "enabled": True, "api_key": "sk-ant-123"}]
        },
    )

    # The registry was refreshed on save, so the provider shows up without a
    # server restart.
    after = {p["name"] for p in client.get("/providers").json()}
    assert "anthropic" in after


def test_ollama_mode_and_endpoints_round_trip(client):
    client.put(
        "/llm-config",
        json={
            "providers": [
                {
                    "provider_name": "ollama",
                    "enabled": True,
                    "ollama_mode": "cloud",
                    "ollama_local_base_url": "http://localhost:11434",
                    "ollama_cloud_base_url": "https://ollama.example.com",
                }
            ]
        },
    )
    body = client.get("/llm-config").json()
    ollama = next(p for p in body["providers"] if p["provider_name"] == "ollama")
    assert ollama["ollama_mode"] == "cloud"
    assert ollama["ollama_local_base_url"] == "http://localhost:11434"
    assert ollama["ollama_cloud_base_url"] == "https://ollama.example.com"


def test_put_rejects_duplicate_providers(client):
    resp = client.put(
        "/llm-config",
        json={
            "providers": [
                {"provider_name": "openai", "enabled": True},
                {"provider_name": "openai", "enabled": False},
            ]
        },
    )
    assert resp.status_code == 400
