"use client";

import { useEffect, useRef, useState } from "react";
import { api, type AgentStage } from "@/lib/api";
import { pipelineRunWsUrl } from "@/lib/pipelineWs";

// The fixed pipeline order, used to render placeholder rows while a run is in
// flight so the user sees the chain before any stage returns. The backend sends
// the authoritative order in the `pipeline_start` event; this is the fallback.
const ROLES = ["planner", "architect", "coding", "review", "testing"] as const;

/**
 * Drives the autonomous Planner→Architect→Coding→Review→Testing pipeline (F11).
 *
 * Streams over the `/agents/run/ws` WebSocket so each stage's output appears the
 * moment that stage finishes, rather than blocking on the whole chain. If the
 * socket can't be opened, it falls back to the synchronous POST /agents/run.
 */
export default function AgentPipeline({ projectId }: { projectId: string | null }) {
  const [goal, setGoal] = useState("");
  const [stages, setStages] = useState<AgentStage[]>([]);
  const [roles, setRoles] = useState<readonly string[]>(ROLES);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const wsRef = useRef<WebSocket | null>(null);

  // Tear down any open socket if the component unmounts mid-run.
  useEffect(() => {
    return () => wsRef.current?.close();
  }, []);

  // Synchronous fallback used when the WebSocket fails to open at all.
  async function runViaRest(trimmed: string) {
    try {
      const res = await api.runAgents(trimmed, projectId ?? undefined);
      setStages(res.stages);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Pipeline run failed");
    } finally {
      setBusy(false);
    }
  }

  function run(e: React.FormEvent) {
    e.preventDefault();
    const trimmed = goal.trim();
    if (!trimmed || busy) return;
    setBusy(true);
    setError(null);
    setStages([]);
    setRoles(ROLES);

    let opened = false;
    let finished = false;

    let ws: WebSocket;
    try {
      ws = new WebSocket(pipelineRunWsUrl());
    } catch {
      void runViaRest(trimmed);
      return;
    }
    wsRef.current = ws;

    ws.onopen = () => {
      opened = true;
      ws.send(JSON.stringify({ goal: trimmed, project_id: projectId ?? null }));
    };

    ws.onmessage = (event) => {
      let msg: {
        type: string;
        roles?: string[];
        stage?: AgentStage;
        error?: string;
      };
      try {
        msg = JSON.parse(event.data);
      } catch {
        return;
      }
      if (msg.type === "pipeline_start" && msg.roles?.length) {
        setRoles(msg.roles);
      } else if (msg.type === "pipeline_stage" && msg.stage) {
        setStages((prev) => [...prev, msg.stage as AgentStage]);
      } else if (msg.type === "pipeline_done") {
        finished = true;
        setBusy(false);
        ws.close();
      } else if (msg.type === "error") {
        finished = true;
        setError(msg.error ?? "Pipeline run failed");
        setBusy(false);
        ws.close();
      }
    };

    ws.onerror = () => {
      // Never opened → fall back to REST. Mid-stream failure → surface it.
      if (!opened) {
        void runViaRest(trimmed);
      } else if (!finished) {
        setError("WebSocket connection failed mid-run");
        setBusy(false);
      }
    };

    ws.onclose = () => {
      wsRef.current = null;
      // Closed before any terminal event (and after opening): stop the spinner.
      if (opened && !finished) setBusy(false);
    };
  }

  // Roles still awaiting a result: everything after the ones already returned.
  const pendingRoles = busy ? roles.slice(stages.length) : [];

  return (
    <div className="flex h-full flex-col rounded-lg border border-neutral-800">
      <div className="border-b border-neutral-800 px-4 py-2 text-sm font-medium">
        Autonomous pipeline
      </div>

      <form onSubmit={run} className="flex gap-2 border-b border-neutral-800 p-3">
        <input
          value={goal}
          onChange={(e) => setGoal(e.target.value)}
          placeholder="Describe a goal, e.g. “Add rate limiting to the API”…"
          className="flex-1 rounded bg-neutral-900 px-3 py-2 text-sm outline-none ring-1 ring-neutral-800 focus:ring-emerald-600"
        />
        <button
          disabled={busy}
          className="rounded bg-emerald-600 px-4 py-2 text-sm font-medium hover:bg-emerald-500 disabled:opacity-50"
        >
          {busy ? "Running…" : "Run"}
        </button>
      </form>

      <div className="flex-1 space-y-3 overflow-y-auto p-4">
        {error && <p className="text-sm text-red-400">{error}</p>}

        {stages.length === 0 && !busy && !error && (
          <p className="text-sm text-neutral-500">
            Each role runs on its own assigned model (set them on the Agents page). The
            goal flows Planner → Architect → Coding → Review → Testing.
          </p>
        )}

        {/* Completed stages stream in live as each one finishes. */}
        {stages.map((s, i) => (
          <StageCard key={i} stage={s} role={s.role} />
        ))}

        {/* Roles not yet returned show as pending placeholders while running. */}
        {pendingRoles.map((role) => (
          <StageCard key={role} role={role} pending />
        ))}
      </div>
    </div>
  );
}

function StageCard({
  role,
  stage,
  pending,
}: {
  role: string;
  stage?: AgentStage;
  pending?: boolean;
}) {
  return (
    <div className="rounded-lg border border-neutral-800">
      <div className="flex items-center justify-between border-b border-neutral-800 px-3 py-1.5">
        <span className="text-sm font-medium capitalize">{role}</span>
        {pending ? (
          <span className="text-[10px] text-neutral-500">waiting…</span>
        ) : (
          <span className="font-mono text-[10px] text-neutral-500">
            {stage?.provider}:{stage?.model}
          </span>
        )}
      </div>
      <div className="px-3 py-2 text-sm">
        {pending ? (
          <div className="h-3 w-2/3 animate-pulse rounded bg-neutral-800" />
        ) : stage?.error ? (
          <p className="text-xs text-red-400">{stage.error}</p>
        ) : (
          <pre className="max-h-48 overflow-y-auto whitespace-pre-wrap text-neutral-300">
            {stage?.output}
          </pre>
        )}
      </div>
    </div>
  );
}
