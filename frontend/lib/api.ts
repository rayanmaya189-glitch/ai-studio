// Typed fetch client to the backend. All paths go through the Next.js
// /api/* rewrite (see next.config.mjs), so they're same-origin in the browser.

import { makeWsUrl } from "@/lib/ws";

const BASE = "/api";

async function http<T>(path: string, init?: RequestInit): Promise<T> {
  const res = await fetch(`${BASE}${path}`, {
    headers: { "Content-Type": "application/json" },
    cache: "no-store",
    ...init,
  });
  if (!res.ok) {
    const detail = await res.text();
    throw new Error(`${res.status} ${res.statusText}: ${detail}`);
  }
  return res.json() as Promise<T>;
}

export interface FsEntry {
  name: string;
  path: string;
  is_dir: boolean;
}

export interface FsListing {
  path: string;
  parent: string | null;
  home: string;
  entries: FsEntry[];
}

export interface Project {
  id: string;
  name: string;
  root_path: string;
  scan_status: string;
  project_metadata: Record<string, unknown>;
  created_at: string;
}

export interface ChatResponse {
  reply: string;
  model: string;
  provider: string;
}

export interface ChatHistoryItem {
  role: string;
  content: string;
  model: string | null;
}

export interface ChatHistoryResponse {
  project_id: string | null;
  session_id: string | null;
  messages: ChatHistoryItem[];
}

export interface ChatSessionsResponse {
  project_id: string;
  sessions: { session_id: string }[];
}

export interface ScanResult {
  project_id: string;
  status: string;
  metadata: Record<string, any>;
}

export interface GraphNode {
  id: string;
  name: string;
  node_type: string;
}
export interface GraphEdge {
  source: string;
  target: string;
}
export interface CodeGraph {
  nodes: GraphNode[];
  edges: GraphEdge[];
}

export interface ProviderInfo {
  name: string;
  available: boolean;
  models: string[];
}

export type OllamaMode = "localhost" | "cloud";

export type ProviderName = "openrouter" | "openai" | "nim" | "ollama" | "anthropic";

// Sent TO the backend. api_key semantics:
//   undefined/null -> leave the stored key unchanged
//   ""             -> clear the stored key
//   "<value>"      -> set/replace the stored key
export interface LLMProviderConfigIn {
  provider_name: ProviderName;
  enabled: boolean;

  api_key?: string | null;
  base_url?: string | null;

  ollama_mode?: OllamaMode;
  ollama_local_base_url?: string | null;
  ollama_cloud_base_url?: string | null;
}

// Returned FROM the backend. The API key is never echoed; has_api_key tells the
// UI whether one is stored.
export interface LLMProviderConfigOut {
  provider_name: ProviderName;
  enabled: boolean;

  has_api_key: boolean;
  base_url: string | null;

  ollama_mode: OllamaMode;
  ollama_local_base_url: string | null;
  ollama_cloud_base_url: string | null;
}

export interface LLMConfigIn {
  providers: LLMProviderConfigIn[];
}

export interface LLMConfigOut {
  providers: LLMProviderConfigOut[];
}

export interface Agent {
  id: string;
  role: string;
  name: string;
  model: string;
}

export interface RagHit {
  source_path: string;
  score: number;
  text: string;
  start_line: number;
  end_line: number;
  symbols: string[];
}
export interface RagSearchResponse {
  project_id: string;
  hits: RagHit[];
}

export interface FileEdit {
  path: string;
  content: string;
}

export interface EditApplyResponse {
  applied: number;
  errors: string[];
}

export interface PullRequestGenerateRequest {
  title: string;
  summary_goal: string;
  model?: string | null;
}

export interface PullRequestGenerateResponse {
  project_id: string;
  title: string;
  provider: string;
  model: string;
  description: string;
}

export interface AgentStage {
  role: string;
  provider: string;
  model: string;
  output: string;
  error: string | null;
}
export interface AgentRunResponse {
  goal: string;
  stages: AgentStage[];
  final_output: string;
}

export type TaskStatus = "pending" | "in_progress" | "blocked" | "completed";

export interface Task {
  id: string;
  project_id: string;
  title: string;
  description: string;
  status: TaskStatus;
  assigned_agent_id: string | null;
}

export interface AgentMemory {
  id: string;
  agent_id: string;
  project_id: string | null;
  kind: string;
  content: string;
  created_at: string;
}

export type ProjectMemoryCategory =
  | "architecture"
  | "services"
  | "standards"
  | "decisions"
  | "history";

export interface ProjectMemory {
  id: string;
  project_id: string;
  category: ProjectMemoryCategory;
  title: string;
  content: string;
  created_at: string;
}

// ---- Project-scoped custom agents / chatbots ----
export interface ProjectAgentOut {
  id: string;
  project_id: string | null;
  kind: string;
  role: string;
  name: string;
  model: string;
  description: string;
  system_prompt: string;
}

export interface ProjectAgentCreate {
  name: string;
  model?: string;
  description?: string;
  system_prompt?: string;
}

export interface ProjectAgentUpdate {
  name?: string | null;
  model?: string | null;
  description?: string | null;
  system_prompt?: string | null;
}

export interface AgentChatRequest {
  message: string;
  remember?: boolean;
}

export interface AgentChatResponse {
  reply: string;
  provider: string;
  model: string;
  used_context: boolean;
  used_private_memory: boolean;
  used_shared_memory: boolean;
}

export interface AgentPrivateMemoryEntry {
  id: string;
  kind: string;
  content: string;
  created_at: string;
}

export const api = {
  // ---- Filesystem browser ----
  fsList: (path?: string, show_hidden = false, include_files = true) => {
    const params = new URLSearchParams();
    if (path) params.set("path", path);
    if (show_hidden) params.set("show_hidden", "true");
    if (!include_files) params.set("include_files", "false");
    return http<FsListing>(`/fs/list?${params.toString()}`);
  },

  // ---- Projects ----
  listProjects: () => http<Project[]>("/projects"),
  createProject: (name: string, root_path: string) =>
    http<Project>("/projects", { method: "POST", body: JSON.stringify({ name, root_path }) }),
  getProject: (projectId: string) => http<Project>(`/projects/${projectId}`),

  // ---- Scan ----
  scan: (projectId: string) => http<ScanResult>(`/scan/${projectId}`, { method: "POST" }),
  metadata: (projectId: string) => http<ScanResult>(`/scan/${projectId}/metadata`),
  graph: (projectId: string) => http<CodeGraph>(`/scan/${projectId}/graph`),

  // ---- Chat ----
  chat: (
    message: string,
    project_id?: string,
    model?: string,
    session_id?: string,
  ) =>
    http<ChatResponse>("/chat", {
      method: "POST",
      body: JSON.stringify({ message, project_id, model, session_id }),
    }),

  // WebSocket chat (streaming)
  // Endpoint: ws://.../api/chat/ws
  chatWsUrl: () => makeWsUrl("/api/chat/ws"),

  chatHistory: (project_id: string, session_id: string | null) =>
    http<ChatHistoryResponse>(
      `/chat/history?project_id=${encodeURIComponent(project_id)}&session_id=${encodeURIComponent(
        session_id ?? "",
      )}`,
    ),

  chatSessions: (project_id: string) =>
    http<ChatSessionsResponse>(`/chat/sessions?project_id=${encodeURIComponent(project_id)}`),

  // ---- RAG ----
  ragSearch: (projectId: string, query: string, limit = 5) =>
    http<RagSearchResponse>(`/rag/${projectId}/search`, {
      method: "POST",
      body: JSON.stringify({ query, limit }),
    }),

  // ---- Agent pipeline ----
  runAgents: (goal: string, project_id?: string, model_map?: Record<string, string>) =>
    http<AgentRunResponse>("/agents/run", {
      method: "POST",
      body: JSON.stringify({ goal, project_id, model_map }),
    }),

  // ---- Code editing ----
  editApply: (projectId: string, edits: FileEdit[]) =>
    http<EditApplyResponse>(`/edit/${projectId}/apply`, {
      method: "POST",
      body: JSON.stringify({ edits }),
    }),

  // ---- Pull requests ----
  generatePullRequest: (projectId: string, title: string, summary_goal: string, model?: string | null) =>
    http<PullRequestGenerateResponse>(
      `/projects/${projectId}/pull-requests/generate`,
      {
        method: "POST",
        body: JSON.stringify({ title, summary_goal, model: model ?? null }),
      },
    ),

  // ---- Providers ----
  providers: () => http<ProviderInfo[]>("/providers"),

  // ---- LLM config ----
  getLlmConfig: () => http<LLMConfigOut>("/llm-config"),
  saveLlmConfig: (providers: LLMProviderConfigIn[]) =>
    http<LLMConfigOut>("/llm-config", {
      method: "PUT",
      body: JSON.stringify({ providers }),
    }),

  // ---- Pipeline agents ----
  agents: () => http<Agent[]>("/agents"),
  setAgentModel: (agentId: string, model: string) =>
    http<Agent>(`/agents/${agentId}/model`, {
      method: "PUT",
      body: JSON.stringify({ model }),
    }),

  // ---- Tasks ----
  listTasks: (projectId: string) => http<Task[]>(`/projects/${projectId}/tasks`),
  createTask: (projectId: string, title: string, description = "", assigned_agent_id?: string) =>
    http<Task>(`/projects/${projectId}/tasks`, {
      method: "POST",
      body: JSON.stringify({ title, description, assigned_agent_id }),
    }),
  updateTask: (
    projectId: string,
    taskId: string,
    patch: Partial<Pick<Task, "title" | "description" | "status" | "assigned_agent_id">>,
  ) =>
    http<Task>(`/projects/${projectId}/tasks/${taskId}`, {
      method: "PATCH",
      body: JSON.stringify(patch),
    }),

  // ---- Project memory ----
  listProjectMemory: (projectId: string) =>
    http<ProjectMemory[]>(`/projects/${projectId}/memory`),
  createProjectMemory: (
    projectId: string,
    category: ProjectMemoryCategory,
    title: string,
    content: string,
  ) =>
    http<ProjectMemory>(`/projects/${projectId}/memory`, {
      method: "POST",
      body: JSON.stringify({ category, title, content }),
    }),

  // ---- Agent memory ----
  listAgentMemory: (agentId: string) => http<AgentMemory[]>(`/agents/${agentId}/memory`),
  createAgentMemory: (agentId: string, content: string, kind = "note", project_id?: string) =>
    http<AgentMemory>(`/agents/${agentId}/memory`, {
      method: "POST",
      body: JSON.stringify({ content, kind, project_id }),
    }),

  // ---- Project-specific custom agents / chatbots ----
  listProjectAgents: (projectId: string) =>
    http<ProjectAgentOut[]>(`/projects/${projectId}/agents`),
  createProjectAgent: (projectId: string, payload: ProjectAgentCreate) =>
    http<ProjectAgentOut>(`/projects/${projectId}/agents`, {
      method: "POST",
      body: JSON.stringify(payload),
    }),
  updateProjectAgent: (projectId: string, agentId: string, payload: ProjectAgentUpdate) =>
    http<ProjectAgentOut>(`/projects/${projectId}/agents/${agentId}`, {
      method: "PATCH",
      body: JSON.stringify(payload),
    }),
  deleteProjectAgent: (projectId: string, agentId: string) =>
    http<{ deleted: string }>(`/projects/${projectId}/agents/${agentId}`, {
      method: "DELETE",
    }),
  chatWithProjectAgent: (projectId: string, agentId: string, payload: AgentChatRequest) =>
    http<AgentChatResponse>(`/projects/${projectId}/agents/${agentId}/chat`, {
      method: "POST",
      body: JSON.stringify(payload),
    }),
  listProjectAgentMemory: (projectId: string, agentId: string) =>
    http<AgentPrivateMemoryEntry[]>(`/projects/${projectId}/agents/${agentId}/memory`),
  shareAgentToProjectMemory: (projectId: string, agentId: string, title: string, content: string, category = "history") =>
    http<{ id: string; category: string; title: string }>(
      `/projects/${projectId}/agents/${agentId}/share`,
      {
        method: "POST",
        body: JSON.stringify({ title, content, category }),
      },
    ),
};