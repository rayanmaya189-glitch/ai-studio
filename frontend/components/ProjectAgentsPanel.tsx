"use client";

import { useEffect, useRef, useState } from "react";
import { api, type ProjectAgentOut, type ProviderInfo } from "@/lib/api";

interface ChatMsg {
  role: "user" | "assistant";
  content: string;
  meta?: string;
  used_context?: boolean;
  used_private_memory?: boolean;
  used_shared_memory?: boolean;
}

export default function ProjectAgentsPanel({
  projectId,
}: {
  projectId: string | null;
}) {
  const [agents, setAgents] = useState<ProjectAgentOut[]>([]);
  const [selectedAgent, setSelectedAgent] = useState<ProjectAgentOut | null>(null);
  const [messages, setMessages] = useState<ChatMsg[]>([]);
  const [input, setInput] = useState("");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [providers, setProviders] = useState<ProviderInfo[]>([]);
  const [showCreate, setShowCreate] = useState(false);
  const [showEdit, setShowEdit] = useState(false);
  const endRef = useRef<HTMLDivElement>(null);

  // Create form state
  const [newName, setNewName] = useState("");
  const [newModel, setNewModel] = useState("");
  const [newDescription, setNewDescription] = useState("");
  const [newSystemPrompt, setNewSystemPrompt] = useState("");

  // Edit form state
  const [editName, setEditName] = useState("");
  const [editModel, setEditModel] = useState("");
  const [editDescription, setEditDescription] = useState("");
  const [editSystemPrompt, setEditSystemPrompt] = useState("");

  useEffect(() => {
    api.providers().then(setProviders).catch(() => {});
  }, []);

  useEffect(() => {
    endRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages]);

  async function refreshAgents() {
    if (!projectId) return;
    try {
      setAgents(await api.listProjectAgents(projectId));
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to load agents");
    }
  }

  useEffect(() => {
    refreshAgents();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [projectId]);

  function selectAgent(agent: ProjectAgentOut) {
    setSelectedAgent(agent);
    setMessages([]);
    setShowCreate(false);
    setShowEdit(false);
  }

  const modelOptions = providers
    .filter((p) => p.available)
    .flatMap((p) => p.models.map((m) => `${p.name}:${m}`));

  async function createAgent(e: React.FormEvent) {
    e.preventDefault();
    if (!projectId || !newName.trim()) return;
    setBusy(true);
    setError(null);
    try {
      await api.createProjectAgent(projectId, {
        name: newName.trim(),
        model: newModel || undefined,
        description: newDescription.trim(),
        system_prompt: newSystemPrompt.trim(),
      });
      setNewName("");
      setNewModel("");
      setNewDescription("");
      setNewSystemPrompt("");
      setShowCreate(false);
      await refreshAgents();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Create failed");
    } finally {
      setBusy(false);
    }
  }

  async function startEdit(agent: ProjectAgentOut) {
    setSelectedAgent(agent);
    setEditName(agent.name);
    setEditModel(agent.model);
    setEditDescription(agent.description);
    setEditSystemPrompt(agent.system_prompt);
    setShowEdit(true);
    setShowCreate(false);
    setMessages([]);
  }

  async function saveEdit(e: React.FormEvent) {
    e.preventDefault();
    if (!projectId || !selectedAgent) return;
    setBusy(true);
    setError(null);
    try {
      await api.updateProjectAgent(projectId, selectedAgent.id, {
        name: editName.trim() || null,
        model: editModel || null,
        description: editDescription.trim() || null,
        system_prompt: editSystemPrompt.trim() || null,
      });
      setShowEdit(false);
      await refreshAgents();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Update failed");
    } finally {
      setBusy(false);
    }
  }

  async function deleteAgent(agent: ProjectAgentOut) {
    if (!projectId || !confirm(`Delete agent "${agent.name}"?`)) return;
    setBusy(true);
    setError(null);
    try {
      await api.deleteProjectAgent(projectId, agent.id);
      if (selectedAgent?.id === agent.id) {
        setSelectedAgent(null);
        setMessages([]);
      }
      await refreshAgents();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Delete failed");
    } finally {
      setBusy(false);
    }
  }

  async function sendMessage(e: React.FormEvent) {
    e.preventDefault();
    if (!projectId || !selectedAgent || !input.trim() || busy) return;
    const text = input;
    setInput("");
    setMessages((prev) => [...prev, { role: "user", content: text }]);
    setBusy(true);
    setError(null);
    try {
      const res = await api.chatWithProjectAgent(projectId, selectedAgent.id, {
        message: text,
        remember: true,
      });
      setMessages((prev) => [
        ...prev,
        {
          role: "assistant",
          content: res.reply,
          meta: `${res.provider}:${res.model}`,
          used_context: res.used_context,
          used_private_memory: res.used_private_memory,
          used_shared_memory: res.used_shared_memory,
        },
      ]);
    } catch (err) {
      setMessages((prev) => [
        ...prev,
        { role: "assistant", content: `Error: ${err}` },
      ]);
    } finally {
      setBusy(false);
    }
  }

  if (!projectId) {
    return (
      <p className="text-sm text-neutral-500">
        Select a project to create and chat with custom agents.
      </p>
    );
  }

  return (
    <div className="flex h-full flex-col rounded-lg border border-neutral-800">
      <div className="flex items-center justify-between border-b border-neutral-800 px-4 py-2">
        <span className="text-sm font-medium">Project agents</span>
        <button
          onClick={() => {
            setShowCreate(true);
            setShowEdit(false);
            setSelectedAgent(null);
            setMessages([]);
          }}
          className="rounded bg-emerald-600 px-3 py-1 text-xs font-medium hover:bg-emerald-500"
        >
          + New agent
        </button>
      </div>

      {error && (
        <div className="border-b border-neutral-800 px-4 py-2 text-xs text-red-400">
          {error}
        </div>
      )}

      {/* Agent list */}
      <div className="flex gap-2 overflow-x-auto border-b border-neutral-800 px-4 py-2">
        {agents.length === 0 && (
          <span className="text-xs text-neutral-600">
            No custom agents yet. Create one to get started.
          </span>
        )}
        {agents.map((agent) => (
          <button
            key={agent.id}
            onClick={() => selectAgent(agent)}
            className={`flex shrink-0 items-center gap-2 rounded-lg px-3 py-2 text-xs transition-colors ${
              selectedAgent?.id === agent.id
                ? "bg-emerald-700/30 ring-1 ring-emerald-600"
                : "bg-neutral-900 ring-1 ring-neutral-800 hover:ring-neutral-600"
            }`}
          >
            <div className="h-2 w-2 rounded-full bg-emerald-500" />
            <span className="font-medium">{agent.name}</span>
            <span className="text-[10px] text-neutral-500">{agent.model}</span>
            <button
              onClick={(e) => {
                e.stopPropagation();
                startEdit(agent);
              }}
              className="ml-1 rounded px-1 py-0.5 text-neutral-600 hover:text-neutral-300"
              title="Edit agent"
            >
              <svg xmlns="http://www.w3.org/2000/svg" className="h-3 w-3" viewBox="0 0 20 20" fill="currentColor">
                <path d="M13.586 3.586a2 2 0 112.828 2.828l-.793.793-2.828-2.828.793-.793zM11.379 5.793L3 14.172V17h2.828l8.38-8.379-2.83-2.828z" />
              </svg>
            </button>
            <button
              onClick={(e) => {
                e.stopPropagation();
                deleteAgent(agent);
              }}
              className="rounded px-1 py-0.5 text-neutral-600 hover:text-red-400"
              title="Delete agent"
            >
              <svg xmlns="http://www.w3.org/2000/svg" className="h-3 w-3" viewBox="0 0 20 20" fill="currentColor">
                <path fillRule="evenodd" d="M9 2a1 1 0 00-.894.553L7.382 4H4a1 1 0 000 2v10a2 2 0 002 2h8a2 2 0 002-2V6a1 1 0 100-2h-3.382l-.724-1.447A1 1 0 0011 2H9zM7 8a1 1 0 012 0v6a1 1 0 11-2 0V8zm5-1a1 1 0 00-1 1v6a1 1 0 102 0V8a1 1 0 00-1-1z" clipRule="evenodd" />
              </svg>
            </button>
          </button>
        ))}
      </div>

      {/* Create form */}
      {showCreate && (
        <form onSubmit={createAgent} className="space-y-3 border-b border-neutral-800 p-4">
          <div className="flex items-center justify-between">
            <span className="text-sm font-medium text-emerald-400">New agent</span>
            <button
              type="button"
              onClick={() => setShowCreate(false)}
              className="text-xs text-neutral-500 hover:text-neutral-300"
            >
              Cancel
            </button>
          </div>
          <div className="grid grid-cols-2 gap-3">
            <div className="col-span-2">
              <label className="block text-xs text-neutral-500">Name *</label>
              <input
                value={newName}
                onChange={(e) => setNewName(e.target.value)}
                required
                placeholder="e.g. Bug Hunter"
                className="mt-1 w-full rounded bg-neutral-900 px-3 py-2 text-sm outline-none ring-1 ring-neutral-800 focus:ring-emerald-600"
              />
            </div>
            <div className="col-span-2">
              <label className="block text-xs text-neutral-500">Description</label>
              <input
                value={newDescription}
                onChange={(e) => setNewDescription(e.target.value)}
                placeholder="What this agent is good at"
                className="mt-1 w-full rounded bg-neutral-900 px-3 py-2 text-sm outline-none ring-1 ring-neutral-800 focus:ring-emerald-600"
              />
            </div>
            <div>
              <label className="block text-xs text-neutral-500">Model</label>
              <select
                value={newModel}
                onChange={(e) => setNewModel(e.target.value)}
                className="mt-1 w-full rounded bg-neutral-900 px-3 py-2 text-sm outline-none ring-1 ring-neutral-800 focus:ring-emerald-600"
              >
                <option value="">Default model</option>
                {modelOptions.map((opt) => (
                  <option key={opt} value={opt}>
                    {opt}
                  </option>
                ))}
              </select>
            </div>
          </div>
          <div>
            <label className="block text-xs text-neutral-500">System prompt (persona)</label>
            <textarea
              value={newSystemPrompt}
              onChange={(e) => setNewSystemPrompt(e.target.value)}
              rows={3}
              placeholder="You are an expert bug hunter. Analyze code deeply and find issues..."
              className="mt-1 w-full resize-y rounded bg-neutral-900 px-3 py-2 text-sm outline-none ring-1 ring-neutral-800 focus:ring-emerald-600"
            />
          </div>
          <button
            disabled={busy || !newName.trim()}
            className="rounded bg-emerald-600 px-4 py-2 text-sm font-medium hover:bg-emerald-500 disabled:opacity-50"
          >
            {busy ? "Creating..." : "Create agent"}
          </button>
        </form>
      )}

      {/* Edit form */}
      {showEdit && selectedAgent && (
        <form onSubmit={saveEdit} className="space-y-3 border-b border-neutral-800 p-4">
          <div className="flex items-center justify-between">
            <span className="text-sm font-medium text-amber-400">
              Edit: {selectedAgent.name}
            </span>
            <button
              type="button"
              onClick={() => setShowEdit(false)}
              className="text-xs text-neutral-500 hover:text-neutral-300"
            >
              Done
            </button>
          </div>
          <div className="grid grid-cols-2 gap-3">
            <div className="col-span-2">
              <label className="block text-xs text-neutral-500">Name</label>
              <input
                value={editName}
                onChange={(e) => setEditName(e.target.value)}
                className="mt-1 w-full rounded bg-neutral-900 px-3 py-2 text-sm outline-none ring-1 ring-neutral-800 focus:ring-emerald-600"
              />
            </div>
            <div className="col-span-2">
              <label className="block text-xs text-neutral-500">Description</label>
              <input
                value={editDescription}
                onChange={(e) => setEditDescription(e.target.value)}
                className="mt-1 w-full rounded bg-neutral-900 px-3 py-2 text-sm outline-none ring-1 ring-neutral-800 focus:ring-emerald-600"
              />
            </div>
            <div>
              <label className="block text-xs text-neutral-500">Model</label>
              <select
                value={editModel}
                onChange={(e) => setEditModel(e.target.value)}
                className="mt-1 w-full rounded bg-neutral-900 px-3 py-2 text-sm outline-none ring-1 ring-neutral-800 focus:ring-emerald-600"
              >
                {modelOptions.map((opt) => (
                  <option key={opt} value={opt}>
                    {opt}
                  </option>
                ))}
              </select>
            </div>
          </div>
          <div>
            <label className="block text-xs text-neutral-500">System prompt</label>
            <textarea
              value={editSystemPrompt}
              onChange={(e) => setEditSystemPrompt(e.target.value)}
              rows={3}
              className="mt-1 w-full resize-y rounded bg-neutral-900 px-3 py-2 text-sm outline-none ring-1 ring-neutral-800 focus:ring-emerald-600"
            />
          </div>
          <button
            disabled={busy || !editName.trim()}
            className="rounded bg-emerald-600 px-4 py-2 text-sm font-medium hover:bg-emerald-500 disabled:opacity-50"
          >
            {busy ? "Saving..." : "Save changes"}
          </button>
        </form>
      )}

      {/* Chat area */}
      {selectedAgent && !showEdit && (
        <div className="flex min-h-0 flex-1 flex-col">
          {/* Agent info header */}
          <div className="flex items-center gap-2 border-b border-neutral-800 px-4 py-2 text-xs text-neutral-500">
            <div className="flex items-center gap-1">
              <span className="font-medium text-neutral-300">{selectedAgent.name}</span>
              <span className="text-neutral-600">·</span>
              <span>{selectedAgent.model}</span>
            </div>
            {selectedAgent.description && (
              <>
                <span className="text-neutral-600">·</span>
                <span className="truncate">{selectedAgent.description}</span>
              </>
            )}
          </div>

          {/* Messages */}
          <div className="flex-1 space-y-3 overflow-y-auto p-4">
            {messages.length === 0 && (
              <div className="space-y-2 text-sm text-neutral-500">
                <p>
                  Ask <strong className="text-neutral-300">{selectedAgent.name}</strong> about the
                  project. This agent has access to:
                </p>
                <ul className="list-inside list-disc space-y-1 text-xs text-neutral-600">
                  <li>Project scan metadata (services, languages, endpoints)</li>
                  <li>RAG-retrieved code context from your codebase</li>
                  <li>Its own private memory (past conversations)</li>
                  <li>Shared project memory (decisions, architecture notes)</li>
                </ul>
              </div>
            )}
            {messages.map((m, i) => (
              <div
                key={i}
                className={m.role === "user" ? "text-right" : "text-left"}
              >
                <div
                  className={`inline-block max-w-[85%] whitespace-pre-wrap rounded-lg px-3 py-2 text-sm ${
                    m.role === "user"
                      ? "bg-emerald-700/40"
                      : "bg-neutral-800"
                  }`}
                >
                  {m.content}
                  {(m.meta || m.used_context !== undefined) && (
                    <div className="mt-1 flex flex-wrap gap-1.5 text-[10px] text-neutral-500">
                      {m.meta && <span>{m.meta}</span>}
                      {m.used_context && (
                        <span className="rounded bg-emerald-900/30 px-1 text-emerald-400">
                          context
                        </span>
                      )}
                      {m.used_private_memory && (
                        <span className="rounded bg-blue-900/30 px-1 text-blue-400">
                          memory
                        </span>
                      )}
                      {m.used_shared_memory && (
                        <span className="rounded bg-purple-900/30 px-1 text-purple-400">
                          shared
                        </span>
                      )}
                    </div>
                  )}
                </div>
              </div>
            ))}
            <div ref={endRef} />
          </div>

          {/* Input */}
          <form onSubmit={sendMessage} className="flex gap-2 border-t border-neutral-800 p-3">
            <input
              value={input}
              onChange={(e) => setInput(e.target.value)}
              placeholder={`Message ${selectedAgent.name}...`}
              className="flex-1 rounded bg-neutral-900 px-3 py-2 text-sm outline-none ring-1 ring-neutral-800 focus:ring-emerald-600"
            />
            <button
              disabled={busy || !input.trim()}
              className="rounded bg-emerald-600 px-4 py-2 text-sm font-medium hover:bg-emerald-500 disabled:opacity-50"
            >
              {busy ? (
                <div className="h-4 w-4 animate-spin rounded-full border-2 border-white border-t-transparent" />
              ) : (
                "Send"
              )}
            </button>
          </form>
        </div>
      )}

      {/* No agent selected */}
      {!selectedAgent && !showCreate && (
        <div className="flex flex-1 items-center justify-center">
          <div className="text-center text-sm text-neutral-500">
            <svg
              xmlns="http://www.w3.org/2000/svg"
              className="mx-auto mb-2 h-10 w-10 text-neutral-700"
              fill="none"
              viewBox="0 0 24 24"
              stroke="currentColor"
              strokeWidth={1}
            >
              <path
                strokeLinecap="round"
                strokeLinejoin="round"
                d="M9.75 3.104v5.714a2.25 2.25 0 01-.659 1.591L5 14.5M9.75 3.104c-.251.023-.501.05-.75.082m.75-.082a24.301 24.301 0 014.5 0m0 0v5.714c0 .597.237 1.17.659 1.591L19.8 15.3M14.25 3.104c.251.023.501.05.75.082M19.8 15.3l-1.57.393A9.065 9.065 0 0112 15a9.065 9.065 0 00-6.23.693L5 14.5m14.8.8l1.402 1.402c1.232 1.232.65 3.318-1.067 3.611A48.309 48.309 0 0112 21c-2.773 0-5.491-.235-8.135-.687-1.718-.293-2.3-2.379-1.067-3.61L5 14.5"
              />
            </svg>
            <p>Select or create a custom agent to start chatting.</p>
            <p className="mt-1 text-xs text-neutral-600">
              Each agent has its own model, persona, and private memory.
            </p>
          </div>
        </div>
      )}
    </div>
  );
}