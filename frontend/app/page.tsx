"use client";

import { useEffect, useState } from "react";
import { api, type Project, type SystemStatusOut } from "@/lib/api";
import FsBrowser from "@/components/FsBrowser";

export default function ProjectsPage() {
  const [projects, setProjects] = useState<Project[]>([]);
  const [name, setName] = useState("");
  const [path, setPath] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);
  const [showFsBrowser, setShowFsBrowser] = useState(false);
  const [hoveredProject, setHoveredProject] = useState<string | null>(null);
  const [filter, setFilter] = useState<string>("all");
  const [status, setStatus] = useState<SystemStatusOut | null>(null);

  async function refresh() {
    try {
      setProjects(await api.listProjects());
    } catch (e) {
      setError(String(e));
    }
  }

  useEffect(() => {
    refresh();
    api.ready().then(setStatus).catch(() => {});
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
      setShowFsBrowser(false);
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

  const filteredProjects = filter === "all"
    ? projects
    : projects.filter((p) => p.scan_status === filter);

  const statusCounts = projects.reduce(
    (acc, p) => {
      acc[p.scan_status] = (acc[p.scan_status] || 0) + 1;
      return acc;
    },
    {} as Record<string, number>,
  );

  return (
    <div className="mx-auto max-w-4xl space-y-8">
      {/* Hero */}
      <div className="space-y-4">
        <div className="flex items-center gap-3">
          <div className="flex h-10 w-10 items-center justify-center rounded-xl bg-emerald-600/20 ring-1 ring-emerald-600/30">
            <svg xmlns="http://www.w3.org/2000/svg" className="h-6 w-6 text-emerald-400" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
              <path strokeLinecap="round" strokeLinejoin="round" d="M10 20l4-16m4 4l4 4-4 4M6 16l-4-4 4-4" />
            </svg>
          </div>
          <div>
            <h1 className="text-2xl font-semibold tracking-tight">
              AI Development Studio
            </h1>
            <p className="text-sm text-neutral-400">
              Multi-agent software engineering platform with RAG, code graphs, and autonomous pipelines.
            </p>
          </div>
        </div>

        <div
          className={`rounded-xl border px-4 py-3 text-sm ${
            status?.ready
              ? "border-emerald-900/60 bg-emerald-950/30 text-emerald-200"
              : "border-amber-900/60 bg-amber-950/30 text-amber-100"
          }`}
        >
          <div className="flex flex-wrap items-center justify-between gap-2">
            <div>
              <div className="font-medium">
                {status?.ready ? "System ready" : "System degraded"}
              </div>
              <div className="text-xs opacity-80">
                {status
                  ? `${status.service} · db ${status.database} · ${status.providers_enabled} provider(s) enabled`
                  : "Checking runtime status..."}
              </div>
            </div>
            {status?.detail && <div className="max-w-xl text-xs opacity-80">{status.detail}</div>}
          </div>
        </div>

        {/* Quick stats */}
        <div className="grid grid-cols-4 gap-3">
          {[
            { label: "Projects", value: projects.length, color: "text-emerald-400" },
            { label: "Scanned", value: statusCounts["completed"] || 0, color: "text-blue-400" },
            { label: "Scanning", value: statusCounts["processing"] || 0, color: "text-amber-400" },
            { label: "Pending", value: statusCounts["pending"] || 0, color: "text-neutral-400" },
          ].map((stat) => (
            <div
              key={stat.label}
              className="rounded-lg border border-neutral-800 bg-neutral-900/50 p-3"
            >
              <div className={`text-2xl font-bold tabular-nums ${stat.color}`}>
                {stat.value}
              </div>
              <div className="text-xs text-neutral-500">{stat.label}</div>
            </div>
          ))}
        </div>
      </div>

      {/* Create project form */}
      <div className="rounded-xl border border-neutral-800 bg-neutral-900/30 p-6">
        <div className="mb-4 flex items-center justify-between">
          <div>
            <h2 className="text-lg font-medium">Add project</h2>
            <p className="text-sm text-neutral-500">
              Point ADS at a project folder. It will be scanned and a knowledge base will be built.
            </p>
          </div>
          <button
            type="button"
            onClick={() => setShowFsBrowser(!showFsBrowser)}
            className={`rounded px-3 py-1.5 text-xs font-medium transition-colors ${
              showFsBrowser
                ? "bg-emerald-600 text-white"
                : "bg-neutral-800 text-neutral-300 hover:bg-neutral-700"
            }`}
          >
            {showFsBrowser ? "Manual path" : "Browse folders"}
          </button>
        </div>

        <form onSubmit={onCreate} className="space-y-4">
          <div className="flex flex-col gap-1">
            <label className="text-sm text-neutral-400">Project name</label>
            <input
              value={name}
              onChange={(e) => setName(e.target.value)}
              required
              placeholder="my-service-mesh"
              className="rounded-lg bg-neutral-950 px-4 py-2.5 text-sm outline-none ring-1 ring-neutral-800 transition-all focus:ring-2 focus:ring-emerald-600"
            />
          </div>

          {showFsBrowser ? (
            <FsBrowser
              onSelect={(p) => {
                setPath(p);
                setShowFsBrowser(false);
              }}
              selectedPath={path}
              label="Browse to your project folder"
              placeholder="/home/you/code/my-project"
            />
          ) : (
            <div className="flex flex-col gap-1">
              <label className="text-sm text-neutral-400">Absolute folder path</label>
              <div className="flex gap-2">
                <input
                  value={path}
                  onChange={(e) => setPath(e.target.value)}
                  required
                  placeholder="/home/you/code/my-project"
                  className="flex-1 rounded-lg bg-neutral-950 px-4 py-2.5 text-sm outline-none ring-1 ring-neutral-800 transition-all focus:ring-2 focus:ring-emerald-600"
                />
                <button
                  type="button"
                  onClick={() => setShowFsBrowser(true)}
                  className="rounded-lg bg-neutral-800 px-3 py-2 text-xs text-neutral-400 hover:bg-neutral-700 hover:text-neutral-200"
                  title="Browse filesystem"
                >
                  <svg xmlns="http://www.w3.org/2000/svg" className="h-5 w-5" viewBox="0 0 20 20" fill="currentColor">
                    <path d="M2 6a2 2 0 012-2h5l2 2h5a2 2 0 012 2v6a2 2 0 01-2 2H4a2 2 0 01-2-2V6z" />
                  </svg>
                </button>
              </div>
            </div>
          )}

          <button
            disabled={busy || !name.trim() || !path.trim()}
            className="flex items-center gap-2 rounded-lg bg-emerald-600 px-5 py-2.5 text-sm font-medium transition-all hover:bg-emerald-500 hover:shadow-lg hover:shadow-emerald-600/20 disabled:opacity-50 disabled:shadow-none"
          >
            {busy ? (
              <>
                <div className="h-4 w-4 animate-spin rounded-full border-2 border-white border-t-transparent" />
                Scanning...
              </>
            ) : (
              <>
                <svg xmlns="http://www.w3.org/2000/svg" className="h-4 w-4" viewBox="0 0 20 20" fill="currentColor">
                  <path fillRule="evenodd" d="M10 3a1 1 0 011 1v5h5a1 1 0 110 2h-5v5a1 1 0 11-2 0v-5H4a1 1 0 110-2h5V4a1 1 0 011-1z" clipRule="evenodd" />
                </svg>
                Add & scan project
              </>
            )}
          </button>
        </form>

        {error && (
          <div className="mt-4 rounded-lg border border-red-800 bg-red-900/20 px-4 py-3 text-sm text-red-400">
            <div className="flex items-start gap-2">
              <svg xmlns="http://www.w3.org/2000/svg" className="mt-0.5 h-4 w-4 shrink-0" viewBox="0 0 20 20" fill="currentColor">
                <path fillRule="evenodd" d="M10 18a8 8 0 100-16 8 8 0 000 16zM8.707 7.293a1 1 0 00-1.414 1.414L8.586 10l-1.293 1.293a1 1 0 101.414 1.414L10 11.414l1.293 1.293a1 1 0 001.414-1.414L11.414 10l1.293-1.293a1 1 0 00-1.414-1.414L10 8.586 8.707 7.293z" clipRule="evenodd" />
              </svg>
              <span>{error}</span>
            </div>
          </div>
        )}
      </div>

      {/* Recent projects */}
      <section className="space-y-4">
        <div className="flex items-center justify-between">
          <div>
            <h2 className="text-lg font-medium">Projects</h2>
            <p className="text-sm text-neutral-500">
              Select a project to enter its workspace.
            </p>
          </div>

          {/* Filter */}
          <div className="flex gap-1 rounded-lg bg-neutral-900 p-1">
            {["all", "completed", "processing", "pending", "error"].map((s) => {
              const count = s === "all" ? projects.length : (statusCounts[s] || 0);
              if (count === 0 && s !== "all") return null;
              return (
                <button
                  key={s}
                  onClick={() => setFilter(s)}
                  className={`rounded-md px-3 py-1 text-xs capitalize transition-colors ${
                    filter === s
                      ? "bg-emerald-600 text-white"
                      : "text-neutral-500 hover:text-neutral-300"
                  }`}
                >
                  {s}
                  <span className="ml-1 tabular-nums opacity-60">({count})</span>
                </button>
              );
            })}
          </div>
        </div>

        {filteredProjects.length === 0 && (
          <div className="flex flex-col items-center justify-center rounded-xl border border-dashed border-neutral-800 py-16">
            <svg xmlns="http://www.w3.org/2000/svg" className="mb-3 h-12 w-12 text-neutral-700" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={1}>
              <path strokeLinecap="round" strokeLinejoin="round" d="M19.5 14.25v-2.625a3.375 3.375 0 00-3.375-3.375h-1.5A1.125 1.125 0 0113.5 7.125v-1.5a3.375 3.375 0 00-3.375-3.375H8.25m6.75 12H9m1.5-12H5.625c-.621 0-1.125.504-1.125 1.125v17.25c0 .621.504 1.125 1.125 1.125h12.75c.621 0 1.125-.504 1.125-1.125V11.25a9 9 0 00-9-9z" />
            </svg>
            <p className="text-sm text-neutral-500">
              {filter === "all"
                ? "No projects yet. Add one above."
                : `No projects with status "${filter}".`}
            </p>
          </div>
        )}

        <div className="grid gap-3 sm:grid-cols-2">
          {filteredProjects.map((p) => {
            const statusColor =
              p.scan_status === "completed"
                ? "bg-emerald-500/20 text-emerald-400 ring-emerald-500/30"
                : p.scan_status === "processing"
                  ? "bg-amber-500/20 text-amber-400 ring-amber-500/30"
                  : p.scan_status === "error"
                    ? "bg-red-500/20 text-red-400 ring-red-500/30"
                    : "bg-neutral-800 text-neutral-400 ring-neutral-700";

            return (
              <div
                key={p.id}
                onClick={() => select(p)}
                onMouseEnter={() => setHoveredProject(p.id)}
                onMouseLeave={() => setHoveredProject(null)}
                className={`group relative cursor-pointer rounded-xl border p-4 transition-all ${
                  hoveredProject === p.id
                    ? "border-emerald-700 bg-emerald-950/20 shadow-lg shadow-emerald-900/10"
                    : "border-neutral-800 bg-neutral-900/50 hover:border-neutral-700"
                }`}
              >
                <div className="flex items-start justify-between gap-3">
                  <div className="min-w-0 flex-1">
                    <div className="flex items-center gap-2">
                      <h3 className="truncate text-sm font-medium">{p.name}</h3>
                      {hoveredProject === p.id && (
                        <svg xmlns="http://www.w3.org/2000/svg" className="h-4 w-4 shrink-0 text-emerald-400" viewBox="0 0 20 20" fill="currentColor">
                          <path fillRule="evenodd" d="M10.293 3.293a1 1 0 011.414 0l6 6a1 1 0 010 1.414l-6 6a1 1 0 01-1.414-1.414L14.586 11H3a1 1 0 110-2h11.586l-4.293-4.293a1 1 0 010-1.414z" clipRule="evenodd" />
                        </svg>
                      )}
                    </div>
                    <p className="mt-1 truncate text-xs text-neutral-500">{p.root_path}</p>
                    <p className="mt-1 text-[10px] text-neutral-600">
                      {new Date(p.created_at).toLocaleDateString(undefined, {
                        year: "numeric",
                        month: "short",
                        day: "numeric",
                      })}
                    </p>
                  </div>
                  <span
                    className={`inline-flex shrink-0 items-center rounded-full px-2.5 py-0.5 text-[10px] font-medium capitalize ring-1 ${
                      p.scan_status === "processing" ? "animate-pulse" : ""
                    } ${statusColor}`}
                  >
                    {p.scan_status === "processing" && (
                      <span className="mr-1.5 h-1.5 w-1.5 animate-pulse rounded-full bg-amber-400" />
                    )}
                    {p.scan_status}
                  </span>
                </div>
              </div>
            );
          })}
        </div>
      </section>
    </div>
  );
}
