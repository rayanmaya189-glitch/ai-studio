"""End-to-end API smoke tests over the stub provider + SQLite."""

from __future__ import annotations

import os
import tempfile


def test_health(client):
    resp = client.get("/health")
    assert resp.status_code == 200
    assert resp.json()["status"] == "ok"


def test_providers_endpoint_lists_stub(client):
    resp = client.get("/providers")
    assert resp.status_code == 200
    body = resp.json()
    names = {p["name"] for p in body}
    assert "stub" in names
    stub = next(p for p in body if p["name"] == "stub")
    assert stub["available"] is True
    assert isinstance(stub["models"], list)
    assert len(stub["models"]) > 0


def test_chat_works_with_no_provider_configured(client):
    resp = client.post("/chat", json={"message": "ping"})
    assert resp.status_code == 200
    body = resp.json()
    assert body["provider"] == "stub"
    assert "ping" in body["reply"]


def test_project_scan_flow(client):
    # Create a project pointing at a temp dir with a couple of source files.
    with tempfile.TemporaryDirectory() as d:
        with open(os.path.join(d, "main.py"), "w") as f:
            f.write("print('hi')\n")
        with open(os.path.join(d, "app.ts"), "w") as f:
            f.write("const x = 1;\n")

        created = client.post("/projects", json={"name": "demo", "root_path": d})
        assert created.status_code == 200
        pid = created.json()["id"]

        scanned = client.post(f"/scan/{pid}")
        assert scanned.status_code == 200
        meta = scanned.json()["metadata"]
        assert meta["file_count"] == 2
        assert meta["languages"]["Python"] == 1
        assert meta["languages"]["TypeScript"] == 1

        graph = client.get(f"/scan/{pid}/graph")
        assert graph.status_code == 200
        assert len(graph.json()["nodes"]) >= 1


def test_agents_seed_and_reassign_model(client):
    agents = client.get("/agents").json()
    assert len(agents) == 7  # seven PRD roles seeded
    coding = next(a for a in agents if a["role"] == "coding")

    updated = client.put(f"/agents/{coding['id']}/model", json={"model": "ollama:qwen2.5-coder"})
    assert updated.status_code == 200
    assert updated.json()["model"] == "ollama:qwen2.5-coder"


def test_task_lifecycle(client):
    with tempfile.TemporaryDirectory() as d:
        pid = client.post("/projects", json={"name": "t", "root_path": d}).json()["id"]
        task = client.post(f"/projects/{pid}/tasks", json={"title": "do thing"}).json()
        assert task["status"] == "pending"

        patched = client.patch(
            f"/projects/{pid}/tasks/{task['id']}", json={"status": "in_progress"}
        )
        assert patched.status_code == 200
        assert patched.json()["status"] == "in_progress"

        bad = client.patch(f"/projects/{pid}/tasks/{task['id']}", json={"status": "nonsense"})
        assert bad.status_code == 400


def test_edit_apply_endpoint_happy_path(client):
    with tempfile.TemporaryDirectory() as d:
        pid = client.post("/projects", json={"name": "edit-demo", "root_path": d}).json()["id"]

        payload = {
            "edits": [
                {"path": "src/new_module.py", "content": "def hello():\n    return 'world'\n"}
            ]
        }
        resp = client.post(f"/edit/{pid}/apply", json=payload)
        assert resp.status_code == 200
        body = resp.json()
        assert body["applied"] == 1
        assert body["errors"] == []

        target = os.path.join(d, "src", "new_module.py")
        with open(target, "r", encoding="utf-8") as fh:
            assert "def hello" in fh.read()


def test_edit_apply_endpoint_blocks_path_traversal(client):
    with tempfile.TemporaryDirectory() as d:
        pid = client.post("/projects", json={"name": "edit-demo", "root_path": d}).json()["id"]

        payload = {"edits": [{"path": "../evil.txt", "content": "pwned\n"}]}
        resp = client.post(f"/edit/{pid}/apply", json=payload)
        assert resp.status_code == 200
        body = resp.json()

        # Endpoint does best-effort apply across edits; this traversal should be blocked.
        assert body["applied"] == 0
        assert len(body["errors"]) == 1
        assert "Path traversal blocked" in body["errors"][0]


def test_pull_request_generate_endpoint_happy_path(client):
    with tempfile.TemporaryDirectory() as d:
        pid = client.post("/projects", json={"name": "pr-demo", "root_path": d}).json()["id"]

        payload = {"title": "Add tenant support", "summary_goal": "Support tenant-specific config"}
        resp = client.post(f"/projects/{pid}/pull-requests/generate", json=payload)
        assert resp.status_code == 200

        body = resp.json()
        assert body["project_id"] == pid
        assert body["title"] == payload["title"]
        assert body["provider"] == "stub"
        assert body["model"] == "echo"
        assert isinstance(body["description"], str)
        assert len(body["description"]) > 0
