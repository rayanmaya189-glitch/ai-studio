"""Code graph engine (F4).

STUB-level: returns a small illustrative service graph (the PRD's
Auth -> User -> Notification -> Event Bus example). The real version will derive
nodes/edges from Tree-sitter symbol analysis and optionally persist to Neo4j.
The return shape matches ``schemas.CodeGraphOut`` so the UI is real now.
"""

from __future__ import annotations


def build_code_graph(project_id: str) -> dict:
    nodes = [
        {"id": "auth", "name": "Auth Service", "node_type": "service"},
        {"id": "user", "name": "User Service", "node_type": "service"},
        {"id": "notification", "name": "Notification Service", "node_type": "service"},
        {"id": "eventbus", "name": "Event Bus", "node_type": "event"},
    ]
    edges = [
        {"source": "auth", "target": "user"},
        {"source": "user", "target": "notification"},
        {"source": "notification", "target": "eventbus"},
    ]
    return {"nodes": nodes, "edges": edges}
