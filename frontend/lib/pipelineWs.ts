import { makeWsUrl } from "@/lib/ws";

export function pipelineRunWsUrl(): string {
  // Backend path: backend/app/api/agents.py websocket endpoint mounted at /agents + /run/ws
  return makeWsUrl("/api/agents/run/ws");
}
