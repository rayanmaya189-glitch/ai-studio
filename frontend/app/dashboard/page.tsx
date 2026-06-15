"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import ServiceGraph from "@/components/ServiceGraph";

export default function DashboardPage() {
  const [projectId, setProjectId] = useState<string | null>(null);

  useEffect(() => {
    setProjectId(localStorage.getItem("ads.projectId"));
  }, []);

  if (!projectId) {
    return (
      <p className="text-sm text-neutral-400">
        No project selected. <Link href="/" className="text-emerald-400 underline">Pick one</Link>.
      </p>
    );
  }

  return (
    <div className="space-y-4">
      <div>
        <h1 className="text-2xl font-semibold">Service Intelligence</h1>
        <p className="text-sm text-neutral-400">
          Service dependencies and event flows. Graph data is illustrative until the Tree-sitter
          code-graph engine lands.
        </p>
      </div>
      <ServiceGraph projectId={projectId} />
    </div>
  );
}
