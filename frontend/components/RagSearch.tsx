"use client";

import { useState } from "react";
import { api, type RagHit } from "@/lib/api";

/** Semantic search over the project's RAG index (F3). */
export default function RagSearch({ projectId }: { projectId: string }) {
  const [query, setQuery] = useState("");
  const [hits, setHits] = useState<RagHit[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [searched, setSearched] = useState(false);

  async function run(e: React.FormEvent) {
    e.preventDefault();
    if (!query.trim()) return;
    setLoading(true);
    setError(null);
    try {
      const res = await api.ragSearch(projectId, query.trim());
      setHits(res.hits);
      setSearched(true);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Search failed");
    } finally {
      setLoading(false);
    }
  }

  return (
    <div className="space-y-2">
      <form onSubmit={run} className="flex gap-2">
        <input
          value={query}
          onChange={(e) => setQuery(e.target.value)}
          placeholder="Search the codebase…"
          className="flex-1 rounded border border-neutral-700 bg-neutral-900 px-2 py-1 text-sm"
        />
        <button
          type="submit"
          disabled={loading}
          className="rounded bg-emerald-600 px-3 py-1 text-sm font-medium disabled:opacity-50"
        >
          {loading ? "…" : "Search"}
        </button>
      </form>

      {error && <p className="text-xs text-red-400">{error}</p>}
      {searched && hits.length === 0 && !error && (
        <p className="text-xs text-neutral-500">No matches. Scan the project to build the index.</p>
      )}

      <ul className="space-y-2">
        {hits.map((h, i) => (
          <li key={i} className="rounded border border-neutral-800 p-2">
            <div className="flex justify-between text-xs text-neutral-400">
              <span className="font-mono">
                {h.source_path}:{h.start_line + 1}
              </span>
              <span className="tabular-nums">{h.score.toFixed(3)}</span>
            </div>
            {h.symbols.length > 0 && (
              <div className="mt-0.5 text-xs text-emerald-400">{h.symbols.join(", ")}</div>
            )}
            <pre className="mt-1 max-h-24 overflow-y-auto whitespace-pre-wrap text-xs text-neutral-300">
              {h.text.slice(0, 400)}
            </pre>
          </li>
        ))}
      </ul>
    </div>
  );
}
