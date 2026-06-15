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

export interface Agent {
  id: string;
  role: string;
  name: string;
  model: string;
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
  providers: () => http<ProviderInfo[]>("/providers"),
  agents: () => http<Agent[]>("/agents"),
  setAgentModel: (agentId: string, model: string) =>
    http<Agent>(`/agents/${agentId}/model`, {
      method: "PUT",
      body: JSON.stringify({ model }),
    }),
};
