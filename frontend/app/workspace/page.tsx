"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import ChatPanel from "@/components/ChatPanel";
import AgentPipeline from "@/components/AgentPipeline";
import RagSearch from "@/components/RagSearch";
import CodeEditPanel from "@/components/CodeEditPanel";
import PullRequestPanel from "@/components/PullRequestPanel";
import TaskBoard from "@/components/TaskBoard";
import MemoryPanel from "@/components/MemoryPanel";
import ProjectAgentsPanel from "@/components/ProjectAgentsPanel";
import { api, type ScanResult } from "@/lib/api";

type Tab = "chat" | "agents" | "editpr" | "tasks" | "project-agents";

const TAB_META: { key: Tab; label: string; icon: string }[] = [
  { key: "chat", label: "Chat", icon: "💬" },
  { key: "agents", label: "Pipeline", icon: "🔄" },
  { key: "project-agents", label: "Custom Agents", icon: "🤖" },
  { key: "editpr", label: "Edit / PR", icon: "✏️" },
  { key: "tasks", label: "Tasks / Memory", icon: "📋" },
];

export default function WorkspacePage() {
  const [projectId, setProjectId] = useState<string | null>(null);
  const [projectName, setProjectName] = useState<string>("");
  const [meta, setMeta] = useState<ScanResult | null>(null);
  const [tab, setTab] = useState<Tab>("chat");
  const [sidebarCollapsed, setSidebarCollapsed] = useState(false);

  useEffect(() => {
    const id = localStorage.getItem("ads.projectId");
    if (!id) return;
    // Validate the stored project still exists before rendering the workspace;
    // a stale localStorage id (e.g. after a DB reset) would otherwise leave the
    // panels making requests against a missing project.
    api
      .getProject(id)
      .then((p) => {
        setProjectId(p.id);
        setProjectName(p.name);
        return api.metadata(p.id).then(setMeta).catch(() => {});
      })
      .catch(() => {
        localStorage.removeItem("ads.projectId");
        localStorage.removeItem("ads.projectName");
        setProjectId(null);
      });
  }, []);

  if (!projectId) {
    return (
      <div className="flex items-center justify-center py-20">
        <div className="text-center">
          <svg xmlns="http://www.w3.org/2000/svg" className="mx-auto mb-4 h-16 w-16 text-neutral-700" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={1}>
            <path strokeLinecap="round" strokeLinejoin="round" d="M20 7l-8-4-8 4m16 0l-8 4m8-4v10l-8 4m0-10L4 7m8 4v10M4 7v10l8 4" />
          </svg>
          <p className="text-lg text-neutral-400">No project selected.</p>
          <Link href="/" className="mt-2 inline-block text-sm text-emerald-400 underline hover:text-emerald-300">
            Pick a project to get started
          </Link>
        </div>
      </div>
    );
  }

  const m = (meta?.metadata ?? {}) as Record<string, any>;
  const langs = (m.languages ?? {}) as Record<string, number>;
  const services = (m.services ?? []) as { name: string; language: string | null }[];
  const databases = (m.databases ?? []) as string[];
  const stats: [string, number | undefined][] = [
    ["Files", m.file_count],
    ["Services", m.service_count],
    ["Endpoints", m.endpoint_count],
    ["Symbols", m.symbol_count],
    ["Databases", m.database_count],
  ];

  const tabTitles: Record<Tab, string> = {
    chat: "Workspace chat",
    agents: "Autonomous pipeline",
    "project-agents": "Project agents",
    editpr: "Code editing & pull requests",
    tasks: "Tasks & project memory",
  };

  return (
    <div className="flex h-[calc(100vh-4rem)] gap-0">
      {/* Tab bar (vertical) */}
      <nav className="flex shrink-0 flex-col gap-1 border-r border-neutral-800 bg-neutral-950 p-2">
        {TAB_META.map(({ key, label, icon }) => (
          <button
            key={key}
            onClick={() => setTab(key)}
            className={`flex items-center gap-2 rounded-lg px-3 py-2.5 text-xs font-medium transition-all ${
              tab === key
                ? "bg-emerald-600/20 text-emerald-300 ring-1 ring-emerald-600/30"
                : "text-neutral-500 hover:bg-neutral-800 hover:text-neutral-300"
            }`}
            title={label}
          >
            <span className="text-base">{icon}</span>
            {!sidebarCollapsed && <span>{label}</span>}
          </button>
        ))}
        <div className="mt-auto border-t border-neutral-800 pt-2">
          <button
            onClick={() => setSidebarCollapsed(!sidebarCollapsed)}
            className="flex w-full items-center justify-center rounded-lg px-2 py-2 text-neutral-600 hover:bg-neutral-800 hover:text-neutral-400"
            title="Toggle sidebar"
          >
            <svg xmlns="http://www.w3.org/2000/svg" className="h-4 w-4" viewBox="0 0 20 20" fill="currentColor">
              <path fillRule="evenodd" d="M3 5a1 1 0 011-1h12a1 1 0 110 2H4a1 1 0 01-1-1zM3 10a1 1 0 011-1h12a1 1 0 110 2H4a1 1 0 01-1-1zM3 15a1 1 0 011-1h6a1 1 0 110 2H4a1 1 0 01-1-1z" clipRule="evenodd" />
            </svg>
          </button>
        </div>
      </nav>

      {/* Main content area */}
      <div className="grid min-w-0 flex-1 grid-cols-3 gap-4 p-4">
        {/* Left sidebar: project metadata & file tree */}
        <aside
          className={`col-span-1 space-y-4 overflow-y-auto rounded-xl border border-neutral-800 bg-neutral-900/30 p-4 ${
            sidebarCollapsed ? "hidden" : ""
          }`}
        >
          {/* Project header */}
          <div className="flex items-center gap-3">
            <div className="flex h-8 w-8 items-center justify-center rounded-lg bg-emerald-600/20 ring-1 ring-emerald-600/30">
              <svg xmlns="http://www.w3.org/2000/svg" className="h-4 w-4 text-emerald-400" viewBox="0 0 20 20" fill="currentColor">
                <path d="M2 6a2 2 0 012-2h5l2 2h5a2 2 0 012 2v6a2 2 0 01-2 2H4a2 2 0 01-2-2V6z" />
              </svg>
            </div>
            <div className="min-w-0">
              <div className="truncate text-sm font-medium">{projectName}</div>
              <div className="text-[10px] text-neutral-600">Project overview</div>
            </div>
          </div>

          {/* Stats grid */}
          <div className="grid grid-cols-2 gap-2">
            {stats
              .filter(([, v]) => typeof v === "number")
              .map(([label, v]) => (
                <div
                  key={label}
                  className="rounded-lg border border-neutral-800 bg-neutral-950/50 p-2.5 transition-colors hover:border-neutral-700"
                >
                  <div className="text-lg font-semibold tabular-nums text-neutral-100">{v}</div>
                  <div className="text-[10px] text-neutral-500">{label}</div>
                </div>
              ))}
          </div>

          {/* Services */}
          {services.length > 0 && (
            <div>
              <div className="mb-2 flex items-center gap-2 text-xs uppercase tracking-wide text-neutral-500">
                <svg xmlns="http://www.w3.org/2000/svg" className="h-3.5 w-3.5" viewBox="0 0 20 20" fill="currentColor">
                  <path fillRule="evenodd" d="M11.49 3.17c-.38-1.56-2.6-1.56-2.98 0a1.532 1.532 0 01-2.286.948c-1.372-.836-2.942.734-2.106 2.106.54.886.061 2.042-.947 2.287-1.561.379-1.561 2.6 0 2.978a1.532 1.532 0 01.947 2.287c-.836 1.372.734 2.942 2.106 2.106a1.532 1.532 0 012.287.947c.379 1.561 2.6 1.561 2.978 0a1.533 1.533 0 012.287-.947c1.372.836 2.942-.734 2.106-2.106a1.533 1.533 0 01.947-2.287c1.561-.379 1.561-2.6 0-2.978a1.532 1.532 0 01-.947-2.287c.836-1.372-.734-2.942-2.106-2.106a1.532 1.532 0 01-2.287-.947zM10 13a3 3 0 100-6 3 3 0 000 6z" clipRule="evenodd" />
                </svg>
                <span>Services</span>
              </div>
              <ul className="space-y-1">
                {services.map((s) => (
                  <li
                    key={s.name}
                    className="flex items-center justify-between rounded-md bg-neutral-950/50 px-3 py-1.5 text-xs"
                  >
                    <span className="font-medium text-neutral-300">{s.name}</span>
                    <span className="text-neutral-500">{s.language ?? "—"}</span>
                  </li>
                ))}
              </ul>
            </div>
          )}

          {/* Databases */}
          {databases.length > 0 && (
            <div>
              <div className="mb-2 text-xs uppercase tracking-wide text-neutral-500">
                Databases
              </div>
              <div className="flex flex-wrap gap-1.5">
                {databases.map((d) => (
                  <span
                    key={d}
                    className="rounded-md bg-neutral-800 px-2 py-1 text-[10px] font-medium text-neutral-300 ring-1 ring-neutral-700"
                  >
                    {d}
                  </span>
                ))}
              </div>
            </div>
          )}

          {/* Languages */}
          <div>
            <div className="mb-2 flex items-center gap-2 text-xs uppercase tracking-wide text-neutral-500">
              <svg xmlns="http://www.w3.org/2000/svg" className="h-3.5 w-3.5" viewBox="0 0 20 20" fill="currentColor">
                <path fillRule="evenodd" d="M10 20a10 10 0 110-20 10 10 0 010 20zm3.56-8.3a7.54 7.54 0 01-1.49 3.44 6.5 6.5 0 01-4.14 0 7.54 7.54 0 01-1.49-3.44H13.56zm-9.73-1A8.45 8.45 0 0110 2a8.45 8.45 0 016.17 2.2 7.5 7.5 0 00-12.34 6.5z" />
              </svg>
              <span>Languages</span>
            </div>
            {Object.keys(langs).length === 0 ? (
              <p className="text-xs text-neutral-600">No scan data.</p>
            ) : (
              <ul className="space-y-1">
                {Object.entries(langs).map(([lang, count]) => (
                  <li
                    key={lang}
                    className="flex items-center justify-between rounded-md bg-neutral-950/50 px-3 py-1.5 text-xs"
                  >
                    <span className="text-neutral-300">{lang}</span>
                    <span className="tabular-nums text-neutral-500">{count} files</span>
                  </li>
                ))}
              </ul>
            )}
          </div>

          {/* Semantic search */}
          <div>
            <div className="mb-2 text-xs uppercase tracking-wide text-neutral-500">
              Semantic search
            </div>
            <RagSearch projectId={projectId} />
          </div>
        </aside>

        {/* Right content panel */}
        <div className={`flex flex-col gap-2 ${sidebarCollapsed ? "col-span-3" : "col-span-2"}`}>
          {/* Tab header */}
          <div className="flex items-center justify-between rounded-lg border border-neutral-800 bg-neutral-900/30 px-4 py-2">
            <h2 className="text-sm font-medium text-neutral-200">
              {tabTitles[tab]}
            </h2>
            <div className="flex gap-1">
              <button
                onClick={() => {/* Could be a help/info button */}}
                className="rounded px-2 py-1 text-xs text-neutral-600 hover:bg-neutral-800 hover:text-neutral-400"
                title="Help"
              >
                ?
              </button>
            </div>
          </div>

          {/* Tab content */}
          <div className="min-h-0 flex-1">
            {tab === "chat" ? (
              <ChatPanel projectId={projectId} />
            ) : tab === "agents" ? (
              <AgentPipeline projectId={projectId} />
            ) : tab === "project-agents" ? (
              <ProjectAgentsPanel projectId={projectId} />
            ) : tab === "tasks" ? (
              <div className="grid h-full grid-cols-1 gap-2 md:grid-cols-2">
                <div className="min-h-0">
                  <TaskBoard projectId={projectId} />
                </div>
                <div className="min-h-0">
                  <MemoryPanel projectId={projectId} />
                </div>
              </div>
            ) : (
              <div className="grid h-full grid-cols-1 gap-2 md:grid-cols-2">
                <div className="min-h-0">
                  <CodeEditPanel projectId={projectId} />
                </div>
                <div className="min-h-0">
                  <PullRequestPanel projectId={projectId} />
                </div>
              </div>
            )}
          </div>
        </div>
      </div>
    </div>
  );
}