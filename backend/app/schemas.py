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


# ---- RAG (F3) ----
class RagSearchRequest(BaseModel):
    query: str
    limit: int = 5


class RagHit(BaseModel):
    source_path: str
    score: float
    text: str
    start_line: int
    end_line: int
    symbols: list[str] = []


class RagSearchResponse(BaseModel):
    project_id: str
    hits: list[RagHit]


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


# ---- Autonomous agent pipeline (F11) ----
class AgentRunRequest(BaseModel):
    goal: str
    project_id: str | None = None  # when set, RAG context is retrieved + threaded
    # Optional per-role "<provider>:<model>" overrides; unset roles use the
    # models assigned in the Agent table (or the configured default).
    model_map: dict[str, str] | None = None


class StageOut(BaseModel):
    role: str
    provider: str
    model: str
    output: str
    error: str | None = None


class AgentRunResponse(BaseModel):
    goal: str
    stages: list[StageOut]
    final_output: str


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
# ---- Code editing (F12) ----
class FileEdit(BaseModel):
    path: str
    content: str


class EditApplyRequest(BaseModel):
    edits: list[FileEdit]


class EditApplyResponse(BaseModel):
    applied: int
    errors: list[str] = []


# ---- Pull request generator (F13) ----
class PullRequestGenerateRequest(BaseModel):
    title: str
    summary_goal: str
    # Optional "<provider>:<model>" override for the PR-generation LLM call.
    model: str | None = None


class PullRequestGenerateResponse(BaseModel):
    project_id: str
    title: str
    provider: str
    model: str
    description: str


class ProviderInfo(BaseModel):
    name: str
    available: bool
    models: list[str]


# ---- LLM Config (DB-backed) ----
from enum import Enum


class ProviderName(str, Enum):
    openrouter = "openrouter"
    openai = "openai"
    nim = "nim"
    ollama = "ollama"
    anthropic = "anthropic"


class LLMProviderConfigIn(BaseModel):
    provider_name: ProviderName
    enabled: bool = False

    api_key: str | None = None
    base_url: str | None = None

    # Ollama only
    ollama_mode: str = "localhost"  # "localhost" | "cloud"
    ollama_local_base_url: str | None = None
    ollama_cloud_base_url: str | None = None


class LLMConfigIn(BaseModel):
    providers: list[LLMProviderConfigIn]


class LLMConfigOut(BaseModel):
    providers: list[LLMProviderConfigIn]
