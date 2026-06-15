"""Code graph engine (F4).

Builds a structural graph from scan results: one node per detected service plus
one per detected database, with edges inferred from cross-service import
references. Nodes are persisted to the ``code_graph`` table so the graph can be
re-served without a rescan; the return shape matches ``schemas.CodeGraphOut`` so
the React Flow dashboard renders it directly.

This is intentionally graph-structural reasoning (service topology), distinct
from the RAG layer's semantic retrieval. A Neo4j backend can later replace the
SQL persistence behind the same ``build_code_graph`` signature.
"""

from __future__ import annotations

import re

from sqlalchemy.orm import Session

from app.models import CodeGraphNode

# A service is "referenced" by another when the other service's import strings
# mention its directory or name. Cheap, language-agnostic, and good enough to
# surface the dependency topology the dashboard cares about.


def _slug(text: str) -> str:
    return re.sub(r"[^a-z0-9]+", "-", text.lower()).strip("-") or "node"


def _infer_edges(services: list[dict], files: list) -> list[tuple[str, str]]:
    """Infer service->service edges from cross-service imports.

    ``files`` are scanner ``FileRecord`` objects. For each file we find which
    service it belongs to (longest matching service path prefix), then look for
    other services' names/paths inside its import strings.
    """
    # Order by path length desc so nested services win the prefix match.
    ordered = sorted(
        [s for s in services if s.get("path") and s["path"] != "."],
        key=lambda s: len(s["path"]),
        reverse=True,
    )

    def owner_of(path: str) -> str | None:
        for svc in ordered:
            prefix = svc["path"].rstrip("/") + "/"
            if path == svc["path"] or path.startswith(prefix):
                return svc["name"]
        return None

    # Token -> service name, for matching import fragments to a target service.
    targets: list[tuple[str, str]] = []
    for svc in services:
        for token in {svc["name"], (svc.get("path") or "").split("/")[-1]}:
            token = token.strip()
            if len(token) >= 3:
                targets.append((token.lower(), svc["name"]))

    edges: set[tuple[str, str]] = set()
    for rec in files:
        src = owner_of(rec.path)
        if not src or not rec.imports:
            continue
        blob = "\n".join(rec.imports).lower()
        for token, dst in targets:
            if dst != src and token in blob:
                edges.add((src, dst))
    return sorted(edges)


def build_code_graph(project_id: str, meta=None, db: Session | None = None) -> dict:
    """Build the code graph for ``project_id``.

    When ``meta`` is provided (fresh scan), derive nodes/edges from it and
    persist them. Otherwise, rebuild the response from the persisted
    ``code_graph`` rows so a GET after a scan still works.
    """
    if meta is not None and db is not None:
        return _build_and_persist(project_id, meta, db)
    if db is not None:
        return _load_persisted(project_id, db)
    return {"nodes": [], "edges": []}


def _build_and_persist(project_id: str, meta, db: Session) -> dict:
    nodes: list[dict] = []
    edges: list[dict] = []
    seen_ids: set[str] = set()

    def add_node(node_id: str, name: str, node_type: str) -> None:
        if node_id in seen_ids:
            return
        seen_ids.add(node_id)
        nodes.append({"id": node_id, "name": name, "node_type": node_type})

    for svc in meta.services:
        add_node(f"svc-{_slug(svc['name'])}", svc["name"], "service")
    for dbname in meta.databases:
        add_node(f"db-{_slug(dbname)}", dbname, "database")

    name_to_id = {svc["name"]: f"svc-{_slug(svc['name'])}" for svc in meta.services}
    for src_name, dst_name in _infer_edges(meta.services, meta.files):
        edges.append({"source": name_to_id[src_name], "target": name_to_id[dst_name]})

    # Persist nodes (callers cleared old rows already). Store edges on the
    # source node as a JSON list of target ids.
    edges_by_source: dict[str, list[str]] = {}
    for e in edges:
        edges_by_source.setdefault(e["source"], []).append(e["target"])
    for n in nodes:
        db.add(
            CodeGraphNode(
                project_id=project_id,
                node_type=n["node_type"],
                name=n["name"],
                edges=edges_by_source.get(n["id"], []),
                attributes={"node_id": n["id"]},
            )
        )

    return {"nodes": nodes, "edges": edges}


def _load_persisted(project_id: str, db: Session) -> dict:
    rows = db.query(CodeGraphNode).filter(CodeGraphNode.project_id == project_id).all()
    nodes: list[dict] = []
    edges: list[dict] = []
    for row in rows:
        node_id = (row.attributes or {}).get("node_id") or f"n-{row.id}"
        nodes.append({"id": node_id, "name": row.name, "node_type": row.node_type})
        for target in row.edges or []:
            edges.append({"source": node_id, "target": target})
    return {"nodes": nodes, "edges": edges}
