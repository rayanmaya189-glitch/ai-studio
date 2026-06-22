"""Tests for the multi-agent LangGraph pipeline (F11).

Requires a "test" provider registered in the DB (see conftest.py).
"""

from __future__ import annotations

import os
import tempfile

import pytest
from app.agents.graph import PIPELINE_ROLES, run_agent_pipeline


def test_pipeline_runs_all_stages_in_order():
    result = run_agent_pipeline("Add a /healthz endpoint", model_map={
        r: "test:test-model" for r in PIPELINE_ROLES
    })
    assert [s.role for s in result.stages] == list(PIPELINE_ROLES)
    assert all(s.output for s in result.stages)
    assert all(s.error is None for s in result.stages)
    assert result.final_output == result.stages[-1].output


def test_pipeline_raises_for_invalid_model():
    """An unresolvable model ref should raise immediately."""
    with pytest.raises(ValueError, match="not configured or enabled"):
        run_agent_pipeline(
            "Refactor the auth module",
            model_map={"planner": "nonexistent:model"},
        )


def test_run_endpoint_returns_full_pipeline(client):
    resp = client.post("/agents/run", json={
        "goal": "Add pagination to the list view",
        "model_map": {r: "test:test-model" for r in PIPELINE_ROLES},
    })
    assert resp.status_code == 200
    body = resp.json()
    assert [s["role"] for s in body["stages"]] == list(PIPELINE_ROLES)
    assert body["final_output"]
    assert all(s["model"] for s in body["stages"])


def test_run_endpoint_with_project_threads_context(client):
    with tempfile.TemporaryDirectory() as d:
        with open(os.path.join(d, "main.py"), "w") as f:
            f.write("def add(a, b):\n    return a + b\n")
        pid = client.post("/projects", json={"name": "p", "root_path": d}).json()["id"]
        client.post(f"/scan/{pid}")

        resp = client.post("/agents/run", json={
            "goal": "Document add()",
            "project_id": pid,
            "model_map": {r: "test:test-model" for r in PIPELINE_ROLES},
        })
        assert resp.status_code == 200
        assert len(resp.json()["stages"]) == len(PIPELINE_ROLES)


def test_run_ws_streams_each_stage_in_order(client):
    """The /run/ws socket emits pipeline_start, one stage event per role in
    pipeline order, then pipeline_done with the last stage's output."""
    with client.websocket_connect("/agents/run/ws") as ws:
        ws.send_json({"goal": "Add a /healthz endpoint"})

        start = ws.receive_json()
        assert start["type"] == "pipeline_start"
        assert start["roles"] == list(PIPELINE_ROLES)

        seen = []
        final_output = ""
        while True:
            msg = ws.receive_json()
            if msg["type"] == "pipeline_stage":
                stage = msg["stage"]
                seen.append(stage["role"])
                assert stage["model"]
                assert stage["error"] is None
                final_output = stage["output"] or final_output
            elif msg["type"] == "pipeline_done":
                assert msg["final_output"] == final_output
                break
            else:  # pragma: no cover - unexpected frame
                raise AssertionError(f"unexpected frame: {msg}")

        # Stages arrived one per role, in the canonical pipeline order.
        assert seen == list(PIPELINE_ROLES)


def test_run_ws_missing_goal_errors(client):
    with client.websocket_connect("/agents/run/ws") as ws:
        ws.send_json({"project_id": None})
        msg = ws.receive_json()
        assert msg["type"] == "error"
        assert "goal" in msg["error"].lower()