// Typed fetch client to the backend. All paths go through the Next.js
// /api/* rewrite (see next.config.mjs), so they're same-origin in the browser.

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

export interface LLMProviderConfig {
  provider_name: string; // "openrouter" | "openai" | "nim" | "ollama" | "anthropic"
  enabled: boolean;

  api_key: string | null;
  base_url: string | null;

  ollama_mode: OllamaMode;
  ollama_local_base_url: string | null;
  ollama_cloud_base_url: string | null;
}

export interface LLMConfig {
  providers: LLMProviderConfig[];
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

export const api = {
  listProjects: () => http<Project[]>("/projects"),
  createProject: (name: string, root_path: string) =>
    http<Project>("/projects", { method: "POST", body: JSON.stringify({ name, root_path }) }),
  scan: (projectId: string) => http<ScanResult>(`/scan/${projectId}`, { method: "POST" }),
  metadata: (projectId: string) => http<ScanResult>(`/scan/${projectId}/metadata`),
  graph: (projectId: string) => http<CodeGraph>(`/scan/${projectId}/graph`),
  chat: (message: string, project_id?: string, model?: string) =>
    http<ChatResponse>("/chat", {
      method: "POST",
      body: JSON.stringify({ message, project_id, model }),
    }),
  ragSearch: (projectId: string, query: string, limit = 5) =>
    http<RagSearchResponse>(`/rag/${projectId}/search`, {
      method: "POST",
      body: JSON.stringify({ query, limit }),
    }),
  runAgents: (goal: string, project_id?: string, model_map?: Record<string, string>) =>
    http<AgentRunResponse>("/agents/run", {
      method: "POST",
      body: JSON.stringify({ goal, project_id, model_map }),
    }),
  editApply: (projectId: string, edits: FileEdit[]) =>
    http<EditApplyResponse>(`/edit/${projectId}/apply`, {
      method: "POST",
      body: JSON.stringify({ edits }),
    }),
  generatePullRequest: (projectId: string, title: string, summary_goal: string, model?: string | null) =>
    http<PullRequestGenerateResponse>(
      `/projects/${projectId}/pull-requests/generate`,
      {
        method: "POST",
        body: JSON.stringify({ title, summary_goal, model: model ?? null }),
      },
    ),
  providers: () => http<ProviderInfo[]>("/providers"),
  agents: () => http<Agent[]>("/agents"),
  setAgentModel: (agentId: string, model: string) =>
    http<Agent>(`/agents/${agentId}/model`, {
      method: "PUT",
      body: JSON.stringify({ model }),
    }),

  // Tasks (F9)
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

  // Project memory (F8)
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

  // Agent memory (F7)
  listAgentMemory: (agentId: string) => http<AgentMemory[]>(`/agents/${agentId}/memory`),
  createAgentMemory: (agentId: string, content: string, kind = "note", project_id?: string) =>
    http<AgentMemory>(`/agents/${agentId}/memory`, {
      method: "POST",
      body: JSON.stringify({ content, kind, project_id }),
    }),
};
