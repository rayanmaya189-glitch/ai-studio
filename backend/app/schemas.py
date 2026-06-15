"""Pydantic request/response models for the API."""

from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, ConfigDict


class ORMModel(BaseModel):
    model_config = ConfigDict(from_attributes=True)


# ---- Projects (F1) ----
class ProjectCreate(BaseModel):
    name: str
    root_path: str


class ProjectOut(ORMModel):
    id: str
    name: str
    root_path: str
    scan_status: str
    project_metadata: dict
    created_at: datetime


# ---- Scan (F2/F4) ----
class ScanResult(BaseModel):
    project_id: str
    status: str
    metadata: dict


class GraphNode(BaseModel):
    id: str
    name: str
    node_type: str


class GraphEdge(BaseModel):
    source: str
    target: str


class CodeGraphOut(BaseModel):
    nodes: list[GraphNode]
    edges: list[GraphEdge]


# ---- Chat (F10) ----
class ChatRequest(BaseModel):
    project_id: str | None = None
    message: str
    model: str | None = None  # "<provider>:<model>" override


class ChatResponse(BaseModel):
    reply: str
    model: str
    provider: str


# ---- Agents (F5/F6) ----
class AgentCreate(BaseModel):
    role: str
    name: str
    model: str


class AgentModelUpdate(BaseModel):
    model: str


class AgentOut(ORMModel):
    id: str
    role: str
    name: str
    model: str


# ---- Tasks (F9) ----
class TaskCreate(BaseModel):
    title: str
    description: str = ""
    assigned_agent_id: str | None = None


class TaskUpdate(BaseModel):
    title: str | None = None
    description: str | None = None
    status: str | None = None
    assigned_agent_id: str | None = None


class TaskOut(ORMModel):
    id: str
    project_id: str
    title: str
    description: str
    status: str
    assigned_agent_id: str | None


# ---- Providers ----
class ProviderInfo(BaseModel):
    name: str
    available: bool
    models: list[str]
