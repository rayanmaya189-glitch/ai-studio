"""Tests for the multi-agent LangGraph pipeline (F11)."""

from __future__ import annotations

from app.agents.graph import PIPELINE_ROLES, run_agent_pipeline


def test_pipeline_runs_all_stages_in_order():
    result = run_agent_pipeline("Add a /healthz endpoint")
    assert [s.role for s in result.stages] == list(PIPELINE_ROLES)
    # Every stage produced output via the stub and recorded no error.
    assert all(s.output for s in result.stages)
    assert all(s.error is None for s in result.stages)
    assert result.final_output == result.stages[-1].output


def test_pipeline_falls_back_to_stub_for_unavailable_provider():
    # ollama isn't running in CI, so the coding role must degrade to stub.
    result = run_agent_pipeline(
        "Refactor the auth module", model_map={"coding": "ollama:qwen2.5-coder"}
    )
    coding = next(s for s in result.stages if s.role == "coding")
    assert coding.provider == "stub"
    assert coding.error is None


def test_run_endpoint_returns_full_pipeline(client):
    resp = client.post("/agents/run", json={"goal": "Add pagination to the list view"})
    assert resp.status_code == 200
    body = resp.json()
    assert [s["role"] for s in body["stages"]] == list(PIPELINE_ROLES)
    assert body["final_output"]
    # Endpoint seeds agents, so each stage carries a resolved model.
    assert all(s["model"] for s in body["stages"])


def test_run_endpoint_with_project_threads_context(client):
    import os
    import tempfile

    with tempfile.TemporaryDirectory() as d:
        with open(os.path.join(d, "main.py"), "w") as f:
            f.write("def add(a, b):\n    return a + b\n")
        pid = client.post("/projects", json={"name": "p", "root_path": d}).json()["id"]
        client.post(f"/scan/{pid}")  # ingest into RAG so retrieval has something

        resp = client.post("/agents/run", json={"goal": "Document add()", "project_id": pid})
        assert resp.status_code == 200
        assert len(resp.json()["stages"]) == len(PIPELINE_ROLES)
