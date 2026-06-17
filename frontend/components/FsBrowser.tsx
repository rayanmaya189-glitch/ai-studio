"use client";

import { useCallback, useEffect, useState } from "react";
import { api, type FsEntry } from "@/lib/api";

interface FsBrowserProps {
  onSelect: (path: string) => void;
  selectedPath: string;
  label?: string;
  showFiles?: boolean;
  placeholder?: string;
}

export default function FsBrowser({
  onSelect,
  selectedPath,
  label = "Folder path",
  showFiles = false,
  placeholder = "/home/you/code/my-project",
}: FsBrowserProps) {
  const [currentPath, setCurrentPath] = useState("");
  const [entries, setEntries] = useState<FsEntry[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [manualPath, setManualPath] = useState(selectedPath);

  const navigate = useCallback(async (path?: string) => {
    setLoading(true);
    setError(null);
    try {
      const listing = await api.fsList(path || undefined, false, showFiles);
      setCurrentPath(listing.path);
      setEntries(listing.entries);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to list directory");
      setEntries([]);
    } finally {
      setLoading(false);
    }
  }, [showFiles]);

  // Initial load from home directory
  useEffect(() => {
    navigate();
  }, [navigate]);

  useEffect(() => {
    setManualPath(selectedPath);
  }, [selectedPath]);

  function goToParent() {
    const parent = currentPath.substring(0, currentPath.lastIndexOf("/"));
    if (parent) navigate(parent || "/");
    else navigate("/");
  }

  function goHome() {
    navigate();
  }

  function handleEntryClick(entry: FsEntry) {
    if (entry.is_dir) {
      navigate(entry.path);
    }
  }

  function handleSelect() {
    onSelect(currentPath);
  }

  function handleManualSelect() {
    if (manualPath.trim()) {
      onSelect(manualPath.trim());
    }
  }

  const isSelected = selectedPath === currentPath;

  return (
    <div className="space-y-3">
      <label className="block text-sm text-neutral-400">{label}</label>

      {/* Manual path input */}
      <div className="flex gap-2">
        <input
          value={manualPath}
          onChange={(e) => setManualPath(e.target.value)}
          placeholder={placeholder}
          className="flex-1 rounded bg-neutral-900 px-3 py-2 text-sm outline-none ring-1 ring-neutral-800 focus:ring-emerald-600"
        />
        <button
          type="button"
          onClick={handleManualSelect}
          className="rounded bg-neutral-800 px-3 py-2 text-xs text-neutral-300 hover:bg-neutral-700"
        >
          Set
        </button>
      </div>

      {/* Browser controls */}
      <div className="flex items-center gap-2 text-xs">
        <button
          type="button"
          onClick={goHome}
          className="rounded bg-neutral-800 px-2 py-1 text-neutral-400 hover:text-neutral-200"
          title="Go to home"
        >
          <svg xmlns="http://www.w3.org/2000/svg" className="h-3.5 w-3.5" viewBox="0 0 20 20" fill="currentColor">
            <path d="M10.707 2.293a1 1 0 00-1.414 0l-7 7a1 1 0 001.414 1.414L4 10.414V17a1 1 0 001 1h2a1 1 0 001-1v-2a1 1 0 011-1h2a1 1 0 011 1v2a1 1 0 001 1h2a1 1 0 001-1v-6.586l.293.293a1 1 0 001.414-1.414l-7-7z" />
          </svg>
        </button>
        <div className="flex-1 truncate rounded bg-neutral-900 px-2 py-1 font-mono text-neutral-300">
          {currentPath || "Loading..."}
        </div>
        <button
          type="button"
          onClick={handleSelect}
          disabled={!currentPath}
          className={`rounded px-2 py-1 font-medium ${
            isSelected
              ? "bg-emerald-600 text-white"
              : "bg-neutral-800 text-neutral-300 hover:bg-neutral-700"
          }`}
        >
          {isSelected ? "✓ Selected" : "Select"}
        </button>
      </div>

      {/* Breadcrumb */}
      <div className="flex flex-wrap items-center gap-1 text-xs text-neutral-500">
        {currentPath.split("/").filter(Boolean).map((part, i, arr) => {
          const pathUpTo = "/" + arr.slice(0, i + 1).join("/");
          return (
            <span key={pathUpTo} className="flex items-center gap-1">
              {i > 0 && <span className="text-neutral-700">/</span>}
              <button
                type="button"
                onClick={() => navigate(pathUpTo)}
                className="rounded px-1 py-0.5 hover:bg-neutral-800 hover:text-neutral-200"
              >
                {part}
              </button>
            </span>
          );
        })}
        {currentPath && (
          <button
            type="button"
            onClick={goToParent}
            className="ml-1 rounded bg-neutral-800 px-1.5 py-0.5 text-neutral-500 hover:text-neutral-200"
          >
            ↑ up
          </button>
        )}
      </div>

      {/* Error */}
      {error && <p className="text-xs text-red-400">{error}</p>}

      {/* Loading */}
      {loading && (
        <div className="flex items-center gap-2 py-2 text-xs text-neutral-500">
          <div className="h-3 w-3 animate-spin rounded-full border-2 border-neutral-600 border-t-emerald-500" />
          Loading...
        </div>
      )}

      {/* Directory listing */}
      {!loading && entries.length > 0 && (
        <div className="max-h-56 overflow-y-auto rounded-lg border border-neutral-800">
          {entries.map((entry) => (
            <button
              key={entry.path}
              type="button"
              onClick={() => handleEntryClick(entry)}
              className={`flex w-full items-center gap-3 px-3 py-2 text-left text-sm transition-colors hover:bg-neutral-800 ${
                selectedPath === entry.path ? "bg-emerald-900/30" : ""
              }`}
            >
              {entry.is_dir ? (
                <svg xmlns="http://www.w3.org/2000/svg" className="h-4 w-4 shrink-0 text-amber-400" viewBox="0 0 20 20" fill="currentColor">
                  <path d="M2 6a2 2 0 012-2h5l2 2h5a2 2 0 012 2v6a2 2 0 01-2 2H4a2 2 0 01-2-2V6z" />
                </svg>
              ) : (
                <svg xmlns="http://www.w3.org/2000/svg" className="h-4 w-4 shrink-0 text-blue-400" viewBox="0 0 20 20" fill="currentColor">
                  <path fillRule="evenodd" d="M4 4a2 2 0 012-2h4.586A2 2 0 0112 2.586L15.414 6A2 2 0 0116 7.414V16a2 2 0 01-2 2H6a2 2 0 01-2-2V4z" clipRule="evenodd" />
                </svg>
              )}
              <span className="flex-1 truncate">{entry.name}</span>
              <span className="shrink-0 text-[10px] text-neutral-600">
                {entry.is_dir ? "dir" : "file"}
              </span>
            </button>
          ))}
        </div>
      )}

      {!loading && entries.length === 0 && !error && (
        <p className="text-xs text-neutral-600">Empty directory</p>
      )}
    </div>
  );
}