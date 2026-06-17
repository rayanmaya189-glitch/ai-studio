"use client";

import { useEffect, useState } from "react";
import { api, type Task, type TaskStatus } from "@/lib/api";

/** F9 - Task management: create, assign-by-status, track across the four states. */
const STATUSES: { key: TaskStatus; label: string }[] = [
  { key: "pending", label: "Pending" },
  { key: "in_progress", label: "In Progress" },
  { key: "blocked", label: "Blocked" },
  { key: "completed", label: "Completed" },
];

export default function TaskBoard({ projectId }: { projectId: string | null }) {
  const [tasks, setTasks] = useState<Task[]>([]);
  const [title, setTitle] = useState("");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);

  async function refresh() {
    if (!projectId) return;
    try {
      setTasks(await api.listTasks(projectId));
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to load tasks");
    }
  }

  useEffect(() => {
    refresh();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [projectId]);

  async function create(e: React.FormEvent) {
    e.preventDefault();
    if (!projectId || !title.trim()) return;
    setBusy(true);
    setError(null);
    try {
      await api.createTask(projectId, title.trim());
      setTitle("");
      await refresh();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Create failed");
    } finally {
      setBusy(false);
    }
  }

  async function setStatus(task: Task, status: TaskStatus) {
    if (!projectId || task.status === status) return;
    // Optimistic update, then reconcile from the server.
    setTasks((prev) => prev.map((t) => (t.id === task.id ? { ...t, status } : t)));
    try {
      await api.updateTask(projectId, task.id, { status });
    } catch (err) {
      setError(err instanceof Error ? err.message : "Update failed");
      await refresh();
    }
  }

  if (!projectId) {
    return <p className="text-sm text-neutral-500">Pick a project to manage tasks.</p>;
  }

  return (
    <div className="flex h-full flex-col rounded-lg border border-neutral-800">
      <div className="border-b border-neutral-800 px-4 py-2 text-sm font-medium">Tasks</div>

      <form onSubmit={create} className="flex gap-2 p-4">
        <input
          value={title}
          onChange={(e) => setTitle(e.target.value)}
          placeholder="New task title…"
          className="flex-1 rounded bg-neutral-900 px-3 py-2 text-sm outline-none ring-1 ring-neutral-800 focus:ring-emerald-600"
        />
        <button
          disabled={busy || !title.trim()}
          className="rounded bg-emerald-600 px-4 py-2 text-sm font-medium hover:bg-emerald-500 disabled:opacity-50"
        >
          {busy ? "…" : "Add"}
        </button>
      </form>

      {error && <p className="px-4 text-sm text-red-400">{error}</p>}

      <div className="grid flex-1 grid-cols-1 gap-3 overflow-y-auto p-4 pt-0 md:grid-cols-2">
        {STATUSES.map(({ key, label }) => {
          const col = tasks.filter((t) => t.status === key);
          return (
            <div key={key} className="rounded border border-neutral-800 p-2">
              <div className="mb-2 flex items-center justify-between text-xs uppercase tracking-wide text-neutral-500">
                <span>{label}</span>
                <span className="tabular-nums">{col.length}</span>
              </div>
              <ul className="space-y-2">
                {col.map((t) => (
                  <li key={t.id} className="rounded bg-neutral-900 p-2 text-sm ring-1 ring-neutral-800">
                    <div>{t.title}</div>
                    <select
                      value={t.status}
                      onChange={(e) => setStatus(t, e.target.value as TaskStatus)}
                      className="mt-1 w-full rounded bg-neutral-950 px-1 py-0.5 text-xs text-neutral-400 ring-1 ring-neutral-800"
                    >
                      {STATUSES.map((s) => (
                        <option key={s.key} value={s.key}>
                          {s.label}
                        </option>
                      ))}
                    </select>
                  </li>
                ))}
                {col.length === 0 && (
                  <li className="text-xs text-neutral-600">—</li>
                )}
              </ul>
            </div>
          );
        })}
      </div>
    </div>
  );
}
