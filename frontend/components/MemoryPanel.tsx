"use client";

import { useEffect, useState } from "react";
import { api, type ProjectMemory, type ProjectMemoryCategory } from "@/lib/api";

/** F8 - Project memory: long-term notes the autonomous pipeline reads back in.
 * Categorized by the PRD's project-memory/ folder taxonomy. */
const CATEGORIES: ProjectMemoryCategory[] = [
  "architecture",
  "services",
  "standards",
  "decisions",
  "history",
];

export default function MemoryPanel({ projectId }: { projectId: string | null }) {
  const [items, setItems] = useState<ProjectMemory[]>([]);
  const [category, setCategory] = useState<ProjectMemoryCategory>("architecture");
  const [title, setTitle] = useState("");
  const [content, setContent] = useState("");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);

  async function refresh() {
    if (!projectId) return;
    try {
      setItems(await api.listProjectMemory(projectId));
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to load memory");
    }
  }

  useEffect(() => {
    refresh();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [projectId]);

  async function create(e: React.FormEvent) {
    e.preventDefault();
    if (!projectId || !title.trim() || !content.trim()) return;
    setBusy(true);
    setError(null);
    try {
      await api.createProjectMemory(projectId, category, title.trim(), content.trim());
      setTitle("");
      setContent("");
      await refresh();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Save failed");
    } finally {
      setBusy(false);
    }
  }

  if (!projectId) {
    return <p className="text-sm text-neutral-500">Pick a project to manage memory.</p>;
  }

  return (
    <div className="flex h-full flex-col rounded-lg border border-neutral-800">
      <div className="border-b border-neutral-800 px-4 py-2 text-sm font-medium">
        Project memory
      </div>

      <form onSubmit={create} className="flex flex-col gap-2 p-4">
        <div className="flex gap-2">
          <select
            value={category}
            onChange={(e) => setCategory(e.target.value as ProjectMemoryCategory)}
            className="rounded bg-neutral-900 px-2 py-2 text-sm capitalize outline-none ring-1 ring-neutral-800 focus:ring-emerald-600"
          >
            {CATEGORIES.map((c) => (
              <option key={c} value={c}>
                {c}
              </option>
            ))}
          </select>
          <input
            value={title}
            onChange={(e) => setTitle(e.target.value)}
            placeholder="Title…"
            className="flex-1 rounded bg-neutral-900 px-3 py-2 text-sm outline-none ring-1 ring-neutral-800 focus:ring-emerald-600"
          />
        </div>
        <textarea
          value={content}
          onChange={(e) => setContent(e.target.value)}
          rows={3}
          placeholder="What should the agents remember about this project?"
          className="w-full resize-y rounded bg-neutral-900 px-3 py-2 text-sm outline-none ring-1 ring-neutral-800 focus:ring-emerald-600"
        />
        <button
          disabled={busy || !title.trim() || !content.trim()}
          className="self-start rounded bg-emerald-600 px-4 py-2 text-sm font-medium hover:bg-emerald-500 disabled:opacity-50"
        >
          {busy ? "Saving…" : "Save note"}
        </button>
        {error && <p className="text-sm text-red-400">{error}</p>}
      </form>

      <ul className="flex-1 space-y-2 overflow-y-auto px-4 pb-4">
        {items.length === 0 && (
          <li className="text-xs text-neutral-600">
            No memory yet. Notes saved here are threaded into the autonomous pipeline.
          </li>
        )}
        {items.map((m) => (
          <li key={m.id} className="rounded border border-neutral-800 p-2">
            <div className="flex items-center justify-between text-xs">
              <span className="rounded bg-neutral-800 px-2 py-0.5 capitalize text-neutral-300">
                {m.category}
              </span>
              <span className="font-medium text-neutral-200">{m.title}</span>
            </div>
            <p className="mt-1 whitespace-pre-wrap text-xs text-neutral-400">{m.content}</p>
          </li>
        ))}
      </ul>
    </div>
  );
}
