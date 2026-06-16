"use client";

import { useState } from "react";
import { api, type EditApplyResponse, type FileEdit } from "@/lib/api";

export default function CodeEditPanel({ projectId }: { projectId: string | null }) {
  const [busy, setBusy] = useState(false);
  const [filePath, setFilePath] = useState("");
  const [content, setContent] = useState("");
  const [result, setResult] = useState<EditApplyResponse | null>(null);
  const [error, setError] = useState<string | null>(null);

  async function apply(e: React.FormEvent) {
    e.preventDefault();
    if (!projectId) return;

    const edits: FileEdit[] = [{ path: filePath.trim(), content }];
    setBusy(true);
    setError(null);
    setResult(null);

    try {
      const res = await api.editApply(projectId, edits);
      setResult(res);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Apply failed");
    } finally {
      setBusy(false);
    }
  }

  if (!projectId) {
    return <p className="text-sm text-neutral-500">Pick a project to edit files.</p>;
  }

  return (
    <div className="flex h-full flex-col rounded-lg border border-neutral-800">
      <div className="border-b border-neutral-800 px-4 py-2 text-sm font-medium">Code edit</div>

      <form onSubmit={apply} className="flex flex-col gap-3 p-4">
        <div>
          <div className="mb-1 text-xs text-neutral-500">File path (under project root)</div>
          <input
            value={filePath}
            onChange={(e) => setFilePath(e.target.value)}
            placeholder="e.g. backend/app/api/scan.py"
            className="w-full rounded bg-neutral-900 px-3 py-2 text-sm outline-none ring-1 ring-neutral-800 focus:ring-emerald-600"
          />
        </div>

        <div>
          <div className="mb-1 text-xs text-neutral-500">New file content</div>
          <textarea
            value={content}
            onChange={(e) => setContent(e.target.value)}
            rows={14}
            className="w-full resize-y rounded bg-neutral-900 px-3 py-2 text-sm outline-none ring-1 ring-neutral-800 focus:ring-emerald-600"
          />
        </div>

        <div className="flex items-center gap-2">
          <button
            disabled={busy || !filePath.trim()}
            className="rounded bg-emerald-600 px-4 py-2 text-sm font-medium hover:bg-emerald-500 disabled:opacity-50"
          >
            {busy ? "Applying…" : "Apply"}
          </button>

          <button
            type="button"
            disabled={busy}
            className="rounded bg-neutral-900 px-4 py-2 text-sm font-medium ring-1 ring-neutral-800 hover:ring-emerald-600"
            onClick={() => {
              setFilePath("");
              setContent("");
              setResult(null);
              setError(null);
            }}
          >
            Reset
          </button>
        </div>

        {error && <p className="text-sm text-red-400">{error}</p>}

        {result && (
          <div className="rounded border border-neutral-800 p-3">
            <div className="text-sm font-medium">Apply result</div>
            <div className="mt-1 text-xs text-neutral-400">
              applied: <span className="font-mono text-neutral-300">{result.applied}</span>
            </div>
            {result.errors.length > 0 && (
              <div className="mt-2 text-xs text-red-400">
                {result.errors.map((e, i) => (
                  <div key={i}>{e}</div>
                ))}
              </div>
            )}
          </div>
        )}
      </form>
    </div>
  );
}
