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
  const [sessionId, setSessionId] = useState<string | null>(null);
  const [sessions, setSessions] = useState<string[]>([]);

  const endRef = useRef<HTMLDivElement>(null);

  const sessionStorageKey = projectId ? `ads.chatSessionId:${projectId}` : null;

  useEffect(() => {
    api.providers()
      .then(setProviders)
      .catch(() => {});
  }, []);

  // Auto-select a default model so chat always sends a valid model ref.
  useEffect(() => {
    if (model) return;
    if (!providers.length) return;

    const first = providers
      .filter((p) => p.available)
      .flatMap((p) => p.models.map((m) => `${p.name}:${m}`))[0];

    if (first) setModel(first);
  }, [providers, model]);

  // Load available sessions and select the active one (persisted in localStorage).
  useEffect(() => {
    if (!projectId || !sessionStorageKey) return;

    api
      .chatSessions(projectId)
      .then((res) => {
        const sessionList = (res.sessions ?? []).map((s) => s.session_id);
        setSessions(sessionList);

        const existing = localStorage.getItem(sessionStorageKey);
        const hasExisting = existing && sessionList.includes(existing);

        if (hasExisting) {
          setSessionId(existing);
          return;
        }

        // If we have sessions already, default to the first.
        if (sessionList.length > 0) {
          localStorage.setItem(sessionStorageKey, sessionList[0]);
          setSessionId(sessionList[0]);
          return;
        }

        // No sessions yet: create a new local session id (will appear after first chat POST).
        const newId = crypto.randomUUID();
        localStorage.setItem(sessionStorageKey, newId);
        setSessionId(newId);
      })
      .catch(() => {
        // Fallback: create/load from localStorage only.
        const existing = localStorage.getItem(sessionStorageKey);
        if (existing) setSessionId(existing);
        else if (!sessionId) {
          const newId = crypto.randomUUID();
          localStorage.setItem(sessionStorageKey, newId);
          setSessionId(newId);
        }
      });
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [projectId, sessionStorageKey]);

  // Load history whenever the selected session changes.
  useEffect(() => {
    if (!projectId || !sessionId) return;

    api
      .chatHistory(projectId, sessionId)
      .then((h) => {
        const enriched: Msg[] = h.messages.map((m) => ({
          role: m.role === "user" ? "user" : "assistant",
          content: m.content,
          meta: m.role === "assistant" && m.model ? m.model : undefined,
        }));

        setMessages(enriched);
      })
      .catch(() => {
        // Do not wipe chat UI on transient history load errors.
      });
  }, [projectId, sessionId]);

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
    if (!projectId || !sessionId) return;

    const text = input;
    setInput("");

    // Optimistic UI: show the user message and an immediate assistant placeholder.
    let placeholderIndex = -1;
    setMessages((m) => {
      const next = [
        ...m,
        { role: "user" as const, content: text },
        { role: "assistant" as const, content: "Assistant is thinking…" },
      ];
      placeholderIndex = next.length - 1;
      return next;
    });

    setBusy(true);

    const ws = new WebSocket(api.chatWsUrl());
    let finished = false;

    function replaceAssistant(content: string, meta?: string) {
      setMessages((m) => {
        const idx =
          placeholderIndex !== -1
            ? placeholderIndex
            : m.findIndex((x, i) => i === m.length - 1 && x.role === "assistant");
        if (idx < 0)
          return [
            ...m,
            { role: "assistant", content, meta },
          ];

        const next = m.slice();
        next[idx] = { role: "assistant", content, meta };
        return next;
      });
    }

    ws.onopen = () => {
      ws.send(
        JSON.stringify({
          project_id: projectId,
          session_id: sessionId,
          message: text,
          model: model || undefined,
          stream: true,
        }),
      );
    };

    ws.onmessage = (event) => {
      try {
        const msg = JSON.parse(event.data);

        if (msg.type === "assistant_message") {
          replaceAssistant(
            msg.content ?? "",
            msg.provider && msg.model ? `${msg.provider}:${msg.model}` : undefined,
          );
        } else if (msg.type === "assistant_done") {
          finished = true;
          ws.close();
        } else if (msg.type === "error") {
          replaceAssistant(`Error: ${msg.error ?? "Unknown error"}`);
        }
      } catch {
        // Ignore malformed messages.
      }
    };

    ws.onerror = () => {
      if (!finished) replaceAssistant("Error: WebSocket failed");
    };

    ws.onclose = async () => {
      if (!projectId || !sessionId) return;
      // Re-load to guarantee persisted history and correct ordering.
      try {
        const h = await api.chatHistory(projectId, sessionId);
        const enriched: Msg[] = h.messages.map((m) => ({
          role: m.role === "user" ? "user" : "assistant",
          content: m.content,
          meta: m.role === "assistant" && m.model ? m.model : undefined,
        }));
        setMessages(enriched);
      } catch {
        // ignore
      } finally {
        setBusy(false);
      }
    };
  }

  return (
    <div className="flex h-full flex-col rounded-lg border border-neutral-800">
      <div className="flex flex-wrap items-center justify-between gap-2 border-b border-neutral-800 px-4 py-2">
        <span className="text-sm font-medium">Workspace chat</span>

        <div className="flex flex-wrap items-center gap-2">
          <select
            value={sessionId ?? ""}
            onChange={(e) => {
              const next = e.target.value || null;
              if (projectId && next) {
                localStorage.setItem(`ads.chatSessionId:${projectId}`, next);
              }
              setSessionId(next);
            }}
            className="rounded bg-neutral-900 px-2 py-1 text-xs ring-1 ring-neutral-800"
            title="Chat session"
            disabled={!projectId}
          >
            {sessions.length === 0 ? <option value="">New session</option> : null}
            {sessions.map((s) => (
              <option key={s} value={s}>
                {s}
              </option>
            ))}
          </select>

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
          disabled={busy}
          className="flex-1 rounded bg-neutral-900 px-3 py-2 text-sm outline-none ring-1 ring-neutral-800 focus:ring-emerald-600 disabled:opacity-70"
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
