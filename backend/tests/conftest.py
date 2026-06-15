"""Test fixtures: a TestClient backed by an isolated SQLite file DB."""

from __future__ import annotations

import os
import tempfile

import pytest

# Point the app at a throwaway SQLite DB before any app module imports settings.
_tmp = tempfile.NamedTemporaryFile(suffix=".db", delete=False)
_tmp.close()
os.environ["DATABASE_URL"] = f"sqlite+pysqlite:///{_tmp.name}"

from fastapi.testclient import TestClient  # noqa: E402

from app.db import init_db  # noqa: E402
from app.main import app  # noqa: E402


@pytest.fixture(scope="session", autouse=True)
def _db() -> None:
    init_db()
    yield
    try:
        os.unlink(_tmp.name)
    except OSError:
        pass


@pytest.fixture
def client() -> TestClient:
    return TestClient(app)
