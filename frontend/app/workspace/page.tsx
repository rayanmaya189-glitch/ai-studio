"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import ChatPanel from "@/components/ChatPanel";
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

  const langs = (meta?.metadata?.languages ?? {}) as Record<string, number>;

  return (
    <div className="grid h-[calc(100vh-7rem)] grid-cols-3 gap-4">
      {/* File-tree / metadata stub */}
      <aside className="col-span-1 space-y-4 overflow-y-auto rounded-lg border border-neutral-800 p-4">
        <div>
          <div className="text-xs uppercase tracking-wide text-neutral-500">Project</div>
          <div className="font-medium">{projectName}</div>
        </div>
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
