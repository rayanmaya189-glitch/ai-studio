"use client";

import { useEffect, useState } from "react";
import { api, type Project } from "@/lib/api";

export default function ProjectsPage() {
  const [projects, setProjects] = useState<Project[]>([]);
  const [name, setName] = useState("");
  const [path, setPath] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);

  async function refresh() {
    try {
      setProjects(await api.listProjects());
    } catch (e) {
      setError(String(e));
    }
  }

  useEffect(() => {
    refresh();
  }, []);

  async function onCreate(e: React.FormEvent) {
    e.preventDefault();
    setBusy(true);
    setError(null);
    try {
      const p = await api.createProject(name, path);
      await api.scan(p.id);
      setName("");
      setPath("");
      await refresh();
    } catch (e) {
      setError(String(e));
    } finally {
      setBusy(false);
    }
  }

  function select(p: Project) {
    localStorage.setItem("ads.projectId", p.id);
    localStorage.setItem("ads.projectName", p.name);
    window.location.href = "/workspace";
  }

  return (
    <div className="mx-auto max-w-3xl space-y-8">
      <section>
        <h1 className="mb-1 text-2xl font-semibold">Select a project</h1>
        <p className="text-sm text-neutral-400">
          Point ADS at a project folder on this machine. On creation it is scanned and a
          knowledge base is built.
        </p>
      </section>

      <form onSubmit={onCreate} className="space-y-3 rounded-lg border border-neutral-800 p-4">
        <div className="flex flex-col gap-1">
          <label className="text-sm text-neutral-400">Project name</label>
          <input
            value={name}
            onChange={(e) => setName(e.target.value)}
            required
            placeholder="my-service-mesh"
            className="rounded bg-neutral-900 px-3 py-2 outline-none ring-1 ring-neutral-800 focus:ring-emerald-600"
          />
        </div>
        <div className="flex flex-col gap-1">
          <label className="text-sm text-neutral-400">Absolute folder path</label>
          <input
            value={path}
            onChange={(e) => setPath(e.target.value)}
            required
            placeholder="/home/you/code/my-project"
            className="rounded bg-neutral-900 px-3 py-2 outline-none ring-1 ring-neutral-800 focus:ring-emerald-600"
          />
        </div>
        <button
          disabled={busy}
          className="rounded bg-emerald-600 px-4 py-2 text-sm font-medium hover:bg-emerald-500 disabled:opacity-50"
        >
          {busy ? "Scanning…" : "Add & scan project"}
        </button>
      </form>

      {error && <p className="text-sm text-red-400">{error}</p>}

      <section className="space-y-2">
        <h2 className="text-sm font-medium text-neutral-400">Recent projects</h2>
        {projects.length === 0 && <p className="text-sm text-neutral-500">No projects yet.</p>}
        <ul className="space-y-2">
          {projects.map((p) => (
            <li
              key={p.id}
              className="flex cursor-pointer items-center justify-between rounded border border-neutral-800 px-4 py-3 hover:border-emerald-700"
              onClick={() => select(p)}
            >
              <div>
                <div className="font-medium">{p.name}</div>
                <div className="text-xs text-neutral-500">{p.root_path}</div>
              </div>
              <span className="rounded bg-neutral-800 px-2 py-0.5 text-xs text-neutral-300">
                {p.scan_status}
              </span>
            </li>
          ))}
        </ul>
      </section>
    </div>
  );
}
