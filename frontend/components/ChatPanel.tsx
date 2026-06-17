"use client";

import { useEffect, useRef, useState } from "react";
import { api, type ProviderInfo } from "@/lib/api";

interface Msg {
  role: "user" | "assistant";
  content: string;
  meta?: string;
}

export default function ChatPanel({ projectId }: { projectId: string | null }) {
  const [messages, setMessages] = useState<Msg[]>([]);
  const [input, setInput] = useState("");
  const [model, setModel] = useState<string>("");
  const [providers, setProviders] = useState<ProviderInfo[]>([]);
  const [busy, setBusy] = useState(false);
  const endRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    api.providers().then(setProviders).catch(() => {});
  }, []);

  useEffect(() => {
    endRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages]);

  // Flatten available providers into "provider:model" options.
  const modelOptions = providers
    .filter((p) => p.available)
    .flatMap((p) => p.models.map((m) => `${p.name}:${m}`));

  async function send(e: React.FormEvent) {
    e.preventDefault();
    if (!input.trim()) return;
    const text = input;
    setInput("");
    setMessages((m) => [...m, { role: "user", content: text }]);
    setBusy(true);
    try {
      const res = await api.chat(text, projectId ?? undefined, model || undefined);
      setMessages((m) => [
        ...m,
        { role: "assistant", content: res.reply, meta: `${res.provider}:${res.model}` },
      ]);
    } catch (err) {
      setMessages((m) => [...m, { role: "assistant", content: `Error: ${err}` }]);
    } finally {
      setBusy(false);
    }
  }

  return (
    <div className="flex h-full flex-col rounded-lg border border-neutral-800">
      <div className="flex items-center justify-between border-b border-neutral-800 px-4 py-2">
        <span className="text-sm font-medium">Workspace chat</span>
        <select
          value={model}
          onChange={(e) => setModel(e.target.value)}
          className="rounded bg-neutral-900 px-2 py-1 text-xs ring-1 ring-neutral-800"
        >
          <option value="">Default model</option>
          {modelOptions.map((opt) => (
            <option key={opt} value={opt}>
              {opt}
            </option>
          ))}
        </select>
      </div>

      <div className="flex-1 space-y-3 overflow-y-auto p-4">
        {messages.length === 0 && (
          <p className="text-sm text-neutral-500">
            Ask about the project. Configure your LLM providers in the LLM Config page.
          </p>
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
              {m.meta && <div className="mt-1 text-[10px] text-neutral-500">{m.meta}</div>}
            </div>
          </div>
        ))}
        <div ref={endRef} />
      </div>

      <form onSubmit={send} className="flex gap-2 border-t border-neutral-800 p-3">
        <input
          value={input}
          onChange={(e) => setInput(e.target.value)}
          placeholder="Message the agent…"
          className="flex-1 rounded bg-neutral-900 px-3 py-2 text-sm outline-none ring-1 ring-neutral-800 focus:ring-emerald-600"
        />
        <button
          disabled={busy}
          className="rounded bg-emerald-600 px-4 py-2 text-sm font-medium hover:bg-emerald-500 disabled:opacity-50"
        >
          {busy ? "…" : "Send"}
        </button>
      </form>
    </div>
  );
}
