"use client";

import { useState } from "react";
import { api, type AgentStage } from "@/lib/api";

// The fixed pipeline order, used to render placeholder rows while a run is in
// flight so the user sees the chain before any stage returns.
const ROLES = ["planner", "architect", "coding", "review", "testing"] as const;

/**
 * Drives the autonomous Planner→Architect→Coding→Review→Testing pipeline (F11):
 * sends a goal to POST /agents/run and renders each stage's output, the model
 * that produced it, and any per-stage error.
 */
export default function AgentPipeline({ projectId }: { projectId: string | null }) {
  const [goal, setGoal] = useState("");
  const [stages, setStages] = useState<AgentStage[]>([]);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);

  async function run(e: React.FormEvent) {
    e.preventDefault();
    if (!goal.trim() || busy) return;
    setBusy(true);
    setError(null);
    setStages([]);
    try {
      const res = await api.runAgents(goal.trim(), projectId ?? undefined);
      setStages(res.stages);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Pipeline run failed");
    } finally {
      setBusy(false);
    }
  }

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

        {/* While running, show the ordered roles as pending placeholders. */}
        {busy &&
          ROLES.map((role) => (
            <StageCard key={role} role={role} pending />
          ))}

        {stages.map((s, i) => (
          <StageCard key={i} stage={s} role={s.role} />
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
