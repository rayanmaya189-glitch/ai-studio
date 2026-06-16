"use client";

import { useState } from "react";
import { api, type PullRequestGenerateResponse } from "@/lib/api";

export default function PullRequestPanel({
  projectId,
}: {
  projectId: string | null;
}) {
  const [title, setTitle] = useState("");
  const [summaryGoal, setSummaryGoal] = useState("");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [res, setRes] = useState<PullRequestGenerateResponse | null>(null);

  async function generate(e: React.FormEvent) {
    e.preventDefault();
    if (!projectId) return;
    if (!title.trim() || !summaryGoal.trim()) return;

    setBusy(true);
    setError(null);
    setRes(null);

    try {
      const out = await api.generatePullRequest(projectId, title.trim(), summaryGoal.trim());
      setRes(out);
    } catch (err) {
      setError(err instanceof Error ? err.message : "PR generation failed");
    } finally {
      setBusy(false);
    }
  }

  if (!projectId) {
    return <p className="text-sm text-neutral-500">Pick a project to generate PRs.</p>;
  }

  return (
    <div className="flex h-full flex-col rounded-lg border border-neutral-800">
      <div className="border-b border-neutral-800 px-4 py-2 text-sm font-medium">
        Pull request generator
      </div>

      <form onSubmit={generate} className="flex flex-col gap-3 p-4">
        <div>
          <div className="mb-1 text-xs text-neutral-500">PR title</div>
          <input
            value={title}
            onChange={(e) => setTitle(e.target.value)}
            placeholder="e.g. Add tenant support"
            className="w-full rounded bg-neutral-900 px-3 py-2 text-sm outline-none ring-1 ring-neutral-800 focus:ring-emerald-600"
          />
        </div>

        <div>
          <div className="mb-1 text-xs text-neutral-500">Summary goal</div>
          <textarea
            value={summaryGoal}
            onChange={(e) => setSummaryGoal(e.target.value)}
            rows={8}
            placeholder="What should this PR accomplish?"
            className="w-full resize-y rounded bg-neutral-900 px-3 py-2 text-sm outline-none ring-1 ring-neutral-800 focus:ring-emerald-600"
          />
        </div>

        <div className="flex items-center gap-2">
          <button
            disabled={busy || !title.trim() || !summaryGoal.trim()}
            className="rounded bg-emerald-600 px-4 py-2 text-sm font-medium hover:bg-emerald-500 disabled:opacity-50"
          >
            {busy ? "Generating…" : "Generate PR description"}
          </button>

          <button
            type="button"
            disabled={busy}
            className="rounded bg-neutral-900 px-4 py-2 text-sm font-medium ring-1 ring-neutral-800 hover:ring-emerald-600"
            onClick={() => {
              setTitle("");
              setSummaryGoal("");
              setRes(null);
              setError(null);
            }}
          >
            Reset
          </button>
        </div>

        {error && <p className="text-sm text-red-400">{error}</p>}

        {res && (
          <div className="rounded border border-neutral-800 p-3">
            <div className="flex items-center justify-between">
              <div className="text-sm font-medium">Generated description</div>
              <div className="text-[10px] text-neutral-500 font-mono">
                {res.provider}:{res.model}
              </div>
            </div>
            <pre className="mt-2 max-h-96 overflow-y-auto whitespace-pre-wrap text-sm text-neutral-300">
              {res.description}
            </pre>
          </div>
        )}
      </form>
    </div>
  );
}
