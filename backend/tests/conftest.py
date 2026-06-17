"""Test fixtures: a TestClient backed by an isolated SQLite file DB.

Bootstraps a test provider so all API and graph tests can run without
external dependencies.
"""

from __future__ import annotations

import os
import tempfile
from typing import Generator

import pytest

# Point the app at a throwaway SQLite DB before any app module imports settings.
_tmp = tempfile.NamedTemporaryFile(suffix=".db", delete=False)
_tmp.close()
os.environ["DATABASE_URL"] = f"sqlite+pysqlite:///{_tmp.name}"
os.environ["TEST_MODE"] = "1"
os.environ["DEFAULT_CHAT_MODEL"] = "test:test-model"
os.environ["DEFAULT_EMBED_MODEL"] = "test:test-model"

from fastapi.testclient import TestClient  # noqa: E402

from app.db import init_db, SessionLocal  # noqa: E402
from app.main import app  # noqa: E402
from app.models import LLMProviderConfig  # noqa: E402
from app.providers.base import LLMProvider, ChatMessage  # noqa: E402
from app.providers.registry import get_registry, reset_registry  # noqa: E402


class TestProvider(LLMProvider):
    """Minimal test provider — no network required."""
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


@pytest.fixture(scope="session", autouse=True)
def _setup() -> Generator[None, None, None]:
    init_db()

    # Seed a "test" provider row in the DB so LLMProviderConfig exists.
    with SessionLocal() as db:
        existing = db.get(LLMProviderConfig, "test")
        if existing is None:
            row = LLMProviderConfig(
                provider_name="test",
                enabled=True,
                api_key="",
                base_url="",
                ollama_mode="localhost",
                ollama_local_base_url="",
                ollama_cloud_base_url="",
            )
            db.add(row)
            db.commit()

    # Reset the registry so it rebuilds from scratch.
    reset_registry()

    # Register the TestProvider directly into the registry after build.
    # Since _build() only knows about specific provider types (ollama, openai, etc.),
    # we inject the test provider explicitly.
    reg = get_registry()
    if "test" not in {p.name for p in reg.all()}:
        reg._register(TestProvider())

    yield

    try:
        os.unlink(_tmp.name)
    except OSError:
        pass


@pytest.fixture
def client() -> TestClient:
    return TestClient(app)