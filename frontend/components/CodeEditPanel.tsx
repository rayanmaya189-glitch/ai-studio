"use client";

import { useState } from "react";
import { DiffEditor, Editor } from "@monaco-editor/react";
import { api, type EditApplyResponse, type FileEdit } from "@/lib/api";

// Pick a Monaco language id from the file extension so syntax highlighting works.
function languageFor(path: string): string {
  const ext = path.split(".").pop()?.toLowerCase() ?? "";
  const map: Record<string, string> = {
    ts: "typescript", tsx: "typescript", js: "javascript", jsx: "javascript",
    py: "python", go: "go", rs: "rust", java: "java", rb: "ruby",
    json: "json", yaml: "yaml", yml: "yaml", md: "markdown", sql: "sql",
    sh: "shell", html: "html", css: "css", toml: "ini",
  };
  return map[ext] ?? "plaintext";
}

export default function CodeEditPanel({ projectId }: { projectId: string | null }) {
  const [busy, setBusy] = useState(false);
  const [loading, setLoading] = useState(false);
  const [filePath, setFilePath] = useState("");
  const [original, setOriginal] = useState("");
  const [content, setContent] = useState("");
  const [showDiff, setShowDiff] = useState(false);
  const [loaded, setLoaded] = useState(false);
  const [result, setResult] = useState<EditApplyResponse | null>(null);
  const [error, setError] = useState<string | null>(null);

  async function load() {
    if (!projectId || !filePath.trim()) return;
    setLoading(true);
    setError(null);
    setResult(null);
    try {
      const res = await api.readFile(projectId, filePath.trim());
      setOriginal(res.content);
      setContent(res.content);
      setLoaded(true);
      if (res.truncated) setError("File is large and was truncated for editing.");
    } catch (err) {
      // A missing file is fine — treat as a new file being created.
      setOriginal("");
      setContent("");
      setLoaded(true);
      setError(err instanceof Error ? `${err.message} (editing as a new file)` : "Load failed");
    } finally {
      setLoading(false);
    }
  }

  async function apply(e: React.FormEvent) {
    e.preventDefault();
    if (!projectId) return;
    const edits: FileEdit[] = [{ path: filePath.trim(), content }];
    setBusy(true);
    setError(null);
    setResult(null);
    try {
      const res = await api.editApply(projectId, edits);
      setResult(res);
      if (res.applied > 0) setOriginal(content); // diff baseline now matches disk
    } catch (err) {
      setError(err instanceof Error ? err.message : "Apply failed");
    } finally {
      setBusy(false);
    }
  }

  if (!projectId) {
    return <p className="text-sm text-neutral-500">Pick a project to edit files.</p>;
  }

  const dirty = content !== original;

  return (
    <div className="flex h-full flex-col rounded-lg border border-neutral-800">
      <div className="flex items-center justify-between border-b border-neutral-800 px-4 py-2">
        <span className="text-sm font-medium">Code edit</span>
        {loaded && (
          <button
            type="button"
            onClick={() => setShowDiff((v) => !v)}
            className="rounded px-2 py-1 text-xs ring-1 ring-neutral-800 hover:ring-emerald-600"
          >
            {showDiff ? "Edit" : "Diff"}
          </button>
        )}
      </div>

      <form onSubmit={apply} className="flex min-h-0 flex-1 flex-col gap-3 p-4">
        <div className="flex items-end gap-2">
          <div className="flex-1">
            <div className="mb-1 text-xs text-neutral-500">File path (under project root)</div>
            <input
              value={filePath}
              onChange={(e) => setFilePath(e.target.value)}
              placeholder="e.g. backend/app/api/scan.py"
              className="w-full rounded bg-neutral-900 px-3 py-2 text-sm outline-none ring-1 ring-neutral-800 focus:ring-emerald-600"
            />
          </div>
          <button
            type="button"
            onClick={load}
            disabled={loading || !filePath.trim()}
            className="rounded bg-neutral-900 px-4 py-2 text-sm font-medium ring-1 ring-neutral-800 hover:ring-emerald-600 disabled:opacity-50"
          >
            {loading ? "Loading…" : "Load"}
          </button>
        </div>

        <div className="min-h-0 flex-1 overflow-hidden rounded border border-neutral-800">
          {showDiff ? (
            <DiffEditor
              original={original}
              modified={content}
              language={languageFor(filePath)}
              theme="vs-dark"
              options={{ readOnly: true, renderSideBySide: true, minimap: { enabled: false } }}
            />
          ) : (
            <Editor
              value={content}
              onChange={(v) => setContent(v ?? "")}
              language={languageFor(filePath)}
              theme="vs-dark"
              options={{ minimap: { enabled: false }, fontSize: 13, scrollBeyondLastLine: false }}
            />
          )}
        </div>

        <div className="flex items-center gap-2">
          <button
            disabled={busy || !filePath.trim()}
            className="rounded bg-emerald-600 px-4 py-2 text-sm font-medium hover:bg-emerald-500 disabled:opacity-50"
          >
            {busy ? "Applying…" : "Apply"}
          </button>
          {dirty && <span className="text-xs text-amber-400">unsaved changes</span>}
          <button
            type="button"
            disabled={busy}
            className="rounded bg-neutral-900 px-4 py-2 text-sm font-medium ring-1 ring-neutral-800 hover:ring-emerald-600"
            onClick={() => {
              setFilePath("");
              setOriginal("");
              setContent("");
              setLoaded(false);
              setShowDiff(false);
              setResult(null);
              setError(null);
            }}
          >
            Reset
          </button>
        </div>

        {error && <p className="text-sm text-red-400">{error}</p>}

        {result && (
          <div className="rounded border border-neutral-800 p-3">
            <div className="text-sm font-medium">Apply result</div>
            <div className="mt-1 text-xs text-neutral-400">
              applied: <span className="font-mono text-neutral-300">{result.applied}</span>
            </div>
            {result.errors.length > 0 && (
              <div className="mt-2 text-xs text-red-400">
                {result.errors.map((e, i) => (
                  <div key={i}>{e}</div>
                ))}
              </div>
            )}
          </div>
        )}
      </form>
    </div>
  );
}
