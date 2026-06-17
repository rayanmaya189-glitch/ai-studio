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
    # Multi-session chat grouping for the workspace chat UI.
    session_id: str | None = None
    message: str
    model: str | None = None  # "<provider>:<model>" override


class ChatResponse(BaseModel):
    reply: str
    model: str
    provider: str


class ChatHistoryItem(BaseModel):
    role: str  # "user" | "assistant"
    content: str
    model: str | None = None


class ChatHistoryResponse(BaseModel):
    project_id: str | None = None
    session_id: str | None = None
    messages: list[ChatHistoryItem] = []


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


# ---- Agent memory (F7) ----
class AgentMemoryCreate(BaseModel):
    content: str
    kind: str = "note"  # task | fix | lesson | note
    project_id: str | None = None


class AgentMemoryOut(ORMModel):
    id: str
    agent_id: str
    project_id: str | None
    kind: str
    content: str
    created_at: datetime


# ---- Project memory (F8) ----
class ProjectMemoryCreate(BaseModel):
    # category must be one of the PRD folders: architecture | services |
    # standards | decisions | history (validated in the store helper).
    category: str
    title: str
    content: str


class ProjectMemoryOut(ORMModel):
    id: str
    project_id: str
    category: str
    title: str
    content: str
    created_at: datetime


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

    # api_key semantics on PUT:
    #   None        -> leave the stored key unchanged (the UI never receives the
    #                  real key, so it sends None when the user didn't retype it)
    #   ""          -> clear the stored key
    #   "<value>"   -> set/replace the stored key
    api_key: str | None = None
    base_url: str | None = None

    # Ollama only
    ollama_mode: str = "localhost"  # "localhost" | "cloud"
    ollama_local_base_url: str | None = None
    ollama_cloud_base_url: str | None = None


class LLMProviderConfigOut(ORMModel):
    """Provider config as returned to the client — the API key is never echoed.

    ``has_api_key`` lets the UI show whether a key is stored without exposing it.
    """

    provider_name: ProviderName
    enabled: bool = False

    has_api_key: bool = False
    base_url: str | None = None

    ollama_mode: str = "localhost"
    ollama_local_base_url: str | None = None
    ollama_cloud_base_url: str | None = None


class LLMConfigIn(BaseModel):
    providers: list[LLMProviderConfigIn]


class LLMConfigOut(BaseModel):
    providers: list[LLMProviderConfigOut]


# ---- Filesystem browser ----
class FsEntry(BaseModel):
    name: str
    path: str
    is_dir: bool


class FsListing(BaseModel):
    path: str
    parent: str | None
    home: str
    entries: list[FsEntry]


# ---- Project-scoped custom agents / chatbots ----
class ProjectAgentCreate(BaseModel):
    name: str
    model: str = ""  # "<provider>:<model>" — configured via LLM Config page
    description: str = ""
    system_prompt: str = ""


class ProjectAgentUpdate(BaseModel):
    name: str | None = None
    model: str | None = None
    description: str | None = None
    system_prompt: str | None = None


class ProjectAgentOut(ORMModel):
    id: str
    project_id: str | None
    kind: str  # "pipeline" | "custom"
    role: str
    name: str
    model: str
    description: str
    system_prompt: str


class AgentChatRequest(BaseModel):
    message: str
    # Persist the exchange to the agent's private memory + shared project memory
    # so future turns (and other agents) stay aware. On by default.
    remember: bool = True


class AgentChatResponse(BaseModel):
    reply: str
    provider: str
    model: str
    # Which grounding sources were actually injected, so the UI can show the
    # user *why* the answer is (or isn't) backed by the codebase.
    used_context: bool
    used_private_memory: bool
    used_shared_memory: bool
