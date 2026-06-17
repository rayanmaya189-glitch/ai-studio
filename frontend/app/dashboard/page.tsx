"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import ServiceGraph from "@/components/ServiceGraph";

export default function DashboardPage() {
  const [projectId, setProjectId] = useState<string | null>(null);
  const [projectName, setProjectName] = useState<string>("");

  useEffect(() => {
    setProjectId(localStorage.getItem("ads.projectId"));
    setProjectName(localStorage.getItem("ads.projectName") || "");
  }, []);

  if (!projectId) {
    return (
      <div className="flex items-center justify-center py-20">
        <div className="text-center">
          <svg xmlns="http://www.w3.org/2000/svg" className="mx-auto mb-4 h-16 w-16 text-neutral-700" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={1}>
            <path strokeLinecap="round" strokeLinejoin="round" d="M9 17v-2m3 2v-4m3 4v-6m2 10H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z" />
          </svg>
          <p className="text-lg text-neutral-400">No project selected.</p>
          <Link href="/" className="mt-2 inline-block text-sm text-emerald-400 underline hover:text-emerald-300">
            Pick a project to see its service graph
          </Link>
        </div>
      </div>
    );
  }

  return (
    <div className="mx-auto max-w-6xl space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <div className="flex items-center gap-2">
            <div className="flex h-8 w-8 items-center justify-center rounded-lg bg-emerald-600/20 ring-1 ring-emerald-600/30">
              <svg xmlns="http://www.w3.org/2000/svg" className="h-4 w-4 text-emerald-400" viewBox="0 0 20 20" fill="currentColor">
                <path fillRule="evenodd" d="M11.49 3.17c-.38-1.56-2.6-1.56-2.98 0a1.532 1.532 0 01-2.286.948c-1.372-.836-2.942.734-2.106 2.106.54.886.061 2.042-.947 2.287-1.561.379-1.561 2.6 0 2.978a1.532 1.532 0 01.947 2.287c-.836 1.372.734 2.942 2.106 2.106a1.532 1.532 0 012.287.947c.379 1.561 2.6 1.561 2.978 0a1.533 1.533 0 012.287-.947c1.372.836 2.942-.734 2.106-2.106a1.533 1.533 0 01.947-2.287c1.561-.379 1.561-2.6 0-2.978a1.532 1.532 0 01-.947-2.287c.836-1.372-.734-2.942-2.106-2.106a1.532 1.532 0 01-2.287-.947zM10 13a3 3 0 100-6 3 3 0 000 6z" clipRule="evenodd" />
              </svg>
            </div>
            <div>
              <h1 className="text-xl font-semibold tracking-tight">
                Service Intelligence
              </h1>
              <p className="text-xs text-neutral-500">Project: {projectName}</p>
            </div>
          </div>
        </div>
        <Link
          href="/workspace"
          className="rounded-lg bg-emerald-600 px-4 py-2 text-xs font-medium hover:bg-emerald-500"
        >
          Open workspace
        </Link>
      </div>

      <div className="rounded-xl border border-neutral-800 bg-neutral-900/30 p-6">
        <div className="mb-4">
          <h2 className="text-sm font-medium">Service dependency graph</h2>
          <p className="text-xs text-neutral-500">
            Dependencies inferred by the Tree-sitter scanner and code-graph engine. Scan a
            project to populate it.
          </p>
        </div>
        <div className="h-[500px] rounded-lg bg-neutral-950/50">
          <ServiceGraph projectId={projectId} />
        </div>
      </div>
    </div>
  );
}