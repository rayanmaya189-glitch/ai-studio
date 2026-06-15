"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import ChatPanel from "@/components/ChatPanel";
import RagSearch from "@/components/RagSearch";
import { api, type ScanResult } from "@/lib/api";

export default function WorkspacePage() {
  const [projectId, setProjectId] = useState<string | null>(null);
  const [projectName, setProjectName] = useState<string>("");
  const [meta, setMeta] = useState<ScanResult | null>(null);

  useEffect(() => {
    const id = localStorage.getItem("ads.projectId");
    setProjectId(id);
    setProjectName(localStorage.getItem("ads.projectName") || "");
    if (id) api.metadata(id).then(setMeta).catch(() => {});
  }, []);

  if (!projectId) {
    return (
      <p className="text-sm text-neutral-400">
        No project selected. <Link href="/" className="text-emerald-400 underline">Pick one</Link>.
      </p>
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

  return (
    <div className="grid h-[calc(100vh-7rem)] grid-cols-3 gap-4">
      {/* File-tree / metadata stub */}
      <aside className="col-span-1 space-y-4 overflow-y-auto rounded-lg border border-neutral-800 p-4">
        <div>
          <div className="text-xs uppercase tracking-wide text-neutral-500">Project</div>
          <div className="font-medium">{projectName}</div>
        </div>
        <div className="grid grid-cols-2 gap-2">
          {stats
            .filter(([, v]) => typeof v === "number")
            .map(([label, v]) => (
              <div key={label} className="rounded border border-neutral-800 p-2">
                <div className="text-lg font-semibold tabular-nums">{v}</div>
                <div className="text-xs text-neutral-500">{label}</div>
              </div>
            ))}
        </div>

        {services.length > 0 && (
          <div>
            <div className="mb-1 text-xs uppercase tracking-wide text-neutral-500">
              Services
            </div>
            <ul className="space-y-1 text-sm">
              {services.map((s) => (
                <li key={s.name} className="flex justify-between">
                  <span>{s.name}</span>
                  <span className="text-neutral-500">{s.language ?? "—"}</span>
                </li>
              ))}
            </ul>
          </div>
        )}

        {databases.length > 0 && (
          <div>
            <div className="mb-1 text-xs uppercase tracking-wide text-neutral-500">
              Databases
            </div>
            <div className="flex flex-wrap gap-1">
              {databases.map((d) => (
                <span
                  key={d}
                  className="rounded bg-neutral-800 px-2 py-0.5 text-xs text-neutral-300"
                >
                  {d}
                </span>
              ))}
            </div>
          </div>
        )}

        <div>
          <div className="mb-1 text-xs uppercase tracking-wide text-neutral-500">
            Languages
          </div>
          {Object.keys(langs).length === 0 && (
            <p className="text-sm text-neutral-500">No scan data.</p>
          )}
          <ul className="space-y-1 text-sm">
            {Object.entries(langs).map(([lang, count]) => (
              <li key={lang} className="flex justify-between">
                <span>{lang}</span>
                <span className="text-neutral-500">{count}</span>
              </li>
            ))}
          </ul>
        </div>
        <div>
          <div className="mb-1 text-xs uppercase tracking-wide text-neutral-500">
            Semantic search
          </div>
          <RagSearch projectId={projectId} />
        </div>

        <div className="text-xs text-neutral-600">
          File tree + Monaco editor land in a later slice; this panel shows scan metadata for now.
        </div>
      </aside>

      {/* Chat */}
      <div className="col-span-2">
        <ChatPanel projectId={projectId} />
      </div>
    </div>
  );
}
