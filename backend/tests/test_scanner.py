"""Unit tests for the tree-sitter project scanner (F2) and code graph (F4)."""

from __future__ import annotations

import os

import pytest

from app.graph.code_graph import build_code_graph
from app.scanner.scanner import scan_project


class _FakeDB:
    """Captures add() calls; build_code_graph only needs add() when persisting."""

    def __init__(self) -> None:
        self.added: list = []

    def add(self, obj) -> None:  # noqa: D401 - mimic Session.add
        self.added.append(obj)


def _write(path: str, content: str) -> None:
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w") as fh:
        fh.write(content)


def _make_repo(root: str) -> None:
    # Service: auth (Python/FastAPI, 2 endpoints, a class + function)
    _write(f"{root}/auth/pyproject.toml", "[project]\nname='auth'\n")
    _write(
        f"{root}/auth/main.py",
        'from fastapi import FastAPI\n'
        "app = FastAPI()\n"
        '@app.get("/login")\n'
        "def login():\n    return 1\n"
        '@app.post("/token")\n'
        "def token():\n    return 2\n"
        "class AuthService:\n    def verify(self):\n        return True\n",
    )
    # Service: users (Go), imports auth -> should create an edge
    _write(f"{root}/users/go.mod", "module example/users\n")
    _write(
        f"{root}/users/main.go",
        'package main\nimport (\n  "fmt"\n  "example/auth"\n)\n'
        'func Handler() { fmt.Println("x") }\n',
    )
    # Infra: declares postgres + redis
    _write(
        f"{root}/docker-compose.yml",
        "services:\n  db:\n    image: postgres:16\n  cache:\n    image: redis:7\n",
    )


def test_scan_extracts_symbols_services_endpoints_databases(tmp_path):
    root = str(tmp_path)
    _make_repo(root)
    meta = scan_project(root)
    d = meta.to_dict()

    assert d["languages"]["Python"] == 1
    assert d["languages"]["Go"] == 1
    # auth + users, both detected via build markers.
    assert d["service_count"] == 2
    names = {s["name"]: s["language"] for s in d["services"]}
    assert names["auth"] == "Python"
    assert names["users"] == "Go"
    # 2 FastAPI routes.
    assert d["endpoint_count"] == 2
    # AuthService + verify + login + token == 4 Python symbols, plus Go Handler.
    assert d["symbol_count"] >= 5
    assert set(d["databases"]) == {"PostgreSQL", "Redis"}
    assert d["parse_errors"] == 0


def test_code_graph_infers_cross_service_edge(tmp_path):
    root = str(tmp_path)
    _make_repo(root)
    meta = scan_project(root)
    graph = build_code_graph("proj", meta, _FakeDB())

    node_types = {n["id"]: n["node_type"] for n in graph["nodes"]}
    assert "svc-auth" in node_types and node_types["svc-auth"] == "service"
    assert "db-postgresql" in node_types and node_types["db-postgresql"] == "database"
    # users imports auth -> directed edge users -> auth.
    assert {"source": "svc-users", "target": "svc-auth"} in graph["edges"]


def test_flat_repo_without_markers_is_one_service(tmp_path):
    root = str(tmp_path)
    _write(f"{root}/script.py", "def hello():\n    return 1\n")
    meta = scan_project(root)
    assert meta.to_dict()["service_count"] == 1
    assert meta.services[0]["language"] == "Python"


def test_missing_path_raises(tmp_path):
    missing = str(tmp_path / "nope")
    with pytest.raises(FileNotFoundError):
        scan_project(missing)
