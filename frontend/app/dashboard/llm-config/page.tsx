"use client";

import { useEffect, useMemo, useState } from "react";
import Link from "next/link";
import {
  api,
  type Agent,
  type LLMProviderConfigOut,
  type LLMProviderConfigIn,
  type OllamaMode,
  type ProviderInfo,
  type ProviderName,
} from "@/lib/api";

const KEYED_PROVIDERS: ProviderName[] = ["openai", "openrouter", "nim", "anthropic"];

type RoleToModelRef = Record<string, string>;

type DraftConfig = {
  provider_name: ProviderName;
  enabled: boolean;
  has_api_key: boolean;
  api_key_input: string;
  base_url: string;
  ollama_mode: OllamaMode;
  ollama_local_base_url: string;
  ollama_cloud_base_url: string;
};

function toDraft(c: LLMProviderConfigOut): DraftConfig {
  return {
    provider_name: c.provider_name,
    enabled: c.enabled,
    has_api_key: c.has_api_key,
    api_key_input: "",
    base_url: c.base_url ?? "",
    ollama_mode: c.ollama_mode ?? "localhost",
    ollama_local_base_url: c.ollama_local_base_url ?? "",
    ollama_cloud_base_url: c.ollama_cloud_base_url ?? "",
  };
}

function toPayload(d: DraftConfig): LLMProviderConfigIn {
  return {
    provider_name: d.provider_name,
    enabled: d.enabled,
    api_key: d.api_key_input === "" ? null : d.api_key_input === CLEAR_SENTINEL ? "" : d.api_key_input,
    base_url: d.base_url.trim() === "" ? null : d.base_url.trim(),
    ollama_mode: d.ollama_mode,
    ollama_local_base_url:
      d.ollama_local_base_url.trim() === "" ? null : d.ollama_local_base_url.trim(),
    ollama_cloud_base_url:
      d.ollama_cloud_base_url.trim() === "" ? null : d.ollama_cloud_base_url.trim(),
  };
}

const CLEAR_SENTINEL = "\0__CLEAR__";

const PROVIDER_ICONS: Record<string, string> = {
  openai: "🔵",
  openrouter: "🟠",
  nim: "🟢",
  ollama: "🦙",
  anthropic: "🟣",
};

export default function LlmConfigPage() {
  const [drafts, setDrafts] = useState<DraftConfig[] | null>(null);
  const [providers, setProviders] = useState<ProviderInfo[] | null>(null);
  const [agents, setAgents] = useState<Agent[] | null>(null);
  const [roleModelMap, setRoleModelMap] = useState<RoleToModelRef>({});

  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [err, setErr] = useState<string | null>(null);
  const [notice, setNotice] = useState<string | null>(null);

  const [modelSearch, setModelSearch] = useState("");

  async function reload() {
    setLoading(true);
    setErr(null);
    try {
      const [cfg, p, a] = await Promise.all([
        api.getLlmConfig(),
        api.providers(),
        api.agents(),
      ]);
      setDrafts(cfg.providers.map(toDraft));
      setProviders(p);
      setAgents(a);
      const initial: RoleToModelRef = {};
      for (const ag of a) initial[ag.role] = ag.model;
      setRoleModelMap(initial);
    } catch (e) {
      setErr(e instanceof Error ? e.message : String(e));
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    reload();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  function patchDraft(name: ProviderName, patch: Partial<DraftConfig>) {
    setDrafts((prev) =>
      prev ? prev.map((d) => (d.provider_name === name ? { ...d, ...patch } : d)) : prev,
    );
  }

  const availableModelRefs = useMemo(() => {
    if (!providers) return [];
    const refs: string[] = [];
    for (const p of providers) {
      if (!p.available) continue;
      for (const m of p.models) refs.push(`${p.name}:${m}`);
    }
    return Array.from(new Set(refs));
  }, [providers]);

  const filteredAvailableModelRefs = useMemo(() => {
    const q = modelSearch.trim().toLowerCase();
    if (!q) return availableModelRefs;
    return availableModelRefs.filter((ref) => ref.toLowerCase().includes(q));
  }, [availableModelRefs, modelSearch]);

  async function saveProviders() {
    if (!drafts) return;
    setSaving(true);
    setErr(null);
    setNotice(null);
    try {
      const saved = await api.saveLlmConfig(drafts.map(toPayload));
      setDrafts(saved.providers.map(toDraft));
      const p = await api.providers();
      setProviders(p);
      setNotice("Provider configuration saved.");
    } catch (e) {
      setErr(e instanceof Error ? e.message : String(e));
    } finally {
      setSaving(false);
    }
  }

  async function applyRoleModels() {
    if (!agents) return;
    setSaving(true);
    setErr(null);
    setNotice(null);
    try {
      for (const a of agents) {
        const chosen = roleModelMap[a.role] ?? a.model;
        if (!chosen || chosen === a.model) continue;
        await api.setAgentModel(a.id, chosen);
      }
      const updated = await api.agents();
      setAgents(updated);
      const next: RoleToModelRef = {};
      for (const ag of updated) next[ag.role] = ag.model;
      setRoleModelMap(next);
      setNotice("Agent role models saved.");
    } catch (e) {
      setErr(e instanceof Error ? e.message : String(e));
    } finally {
      setSaving(false);
    }
  }

  if (loading && !drafts) {
    return (
      <div className="mx-auto max-w-4xl space-y-4">
        <div className="flex items-center gap-3">
          <div className="flex h-10 w-10 items-center justify-center rounded-xl bg-emerald-600/20 ring-1 ring-emerald-600/30">
            <svg xmlns="http://www.w3.org/2000/svg" className="h-6 w-6 text-emerald-400" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
              <path strokeLinecap="round" strokeLinejoin="round" d="M9 3v2m6-2v2M9 19v2m6-2v2M5 9H3m2 6H3m18-6h-2m2 6h-2M7 19h10a2 2 0 002-2V7a2 2 0 00-2-2H7a2 2 0 00-2 2v10a2 2 0 002 2zM9 9h6v6H9V9z" />
            </svg>
          </div>
          <div>
            <h1 className="text-2xl font-semibold">LLM Configuration</h1>
            <p className="text-sm text-neutral-400">Loading configuration...</p>
          </div>
        </div>
      </div>
    );
  }

  const availabilityByName = new Map((providers ?? []).map((p) => [p.name, p]));

  return (
    <div className="mx-auto max-w-4xl space-y-8">
      {/* Header */}
      <div className="flex items-center gap-3">
        <div className="flex h-10 w-10 items-center justify-center rounded-xl bg-emerald-600/20 ring-1 ring-emerald-600/30">
          <svg xmlns="http://www.w3.org/2000/svg" className="h-6 w-6 text-emerald-400" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
            <path strokeLinecap="round" strokeLinejoin="round" d="M9 3v2m6-2v2M9 19v2m6-2v2M5 9H3m2 6H3m18-6h-2m2 6h-2M7 19h10a2 2 0 002-2V7a2 2 0 00-2-2H7a2 2 0 00-2 2v10a2 2 0 002 2zM9 9h6v6H9V9z" />
          </svg>
        </div>
        <div>
          <h1 className="text-2xl font-semibold tracking-tight">LLM Configuration</h1>
          <p className="text-sm text-neutral-400">
            Enable providers, store credentials, and assign models to agent roles.
          </p>
        </div>
      </div>

      {/* Notifications */}
      {err && (
        <div className="rounded-xl border border-red-800 bg-red-900/20 px-4 py-3 text-sm text-red-400">
          <div className="flex items-start gap-2">
            <svg xmlns="http://www.w3.org/2000/svg" className="mt-0.5 h-4 w-4 shrink-0" viewBox="0 0 20 20" fill="currentColor">
              <path fillRule="evenodd" d="M10 18a8 8 0 100-16 8 8 0 000 16zM8.707 7.293a1 1 0 00-1.414 1.414L8.586 10l-1.293 1.293a1 1 0 101.414 1.414L10 11.414l1.293 1.293a1 1 0 001.414-1.414L11.414 10l1.293-1.293a1 1 0 00-1.414-1.414L10 8.586 8.707 7.293z" clipRule="evenodd" />
            </svg>
            <span>{err}</span>
          </div>
        </div>
      )}
      {notice && (
        <div className="rounded-xl border border-emerald-800 bg-emerald-900/20 px-4 py-3 text-sm text-emerald-400">
          <div className="flex items-start gap-2">
            <svg xmlns="http://www.w3.org/2000/svg" className="mt-0.5 h-4 w-4 shrink-0" viewBox="0 0 20 20" fill="currentColor">
              <path fillRule="evenodd" d="M10 18a8 8 0 100-16 8 8 0 000 16zm3.707-9.293a1 1 0 00-1.414-1.414L9 10.586 7.707 9.293a1 1 0 00-1.414 1.414l2 2a1 1 0 001.414 0l4-4z" clipRule="evenodd" />
            </svg>
            <span>{notice}</span>
          </div>
        </div>
      )}

      {/* Providers */}
      <section className="space-y-4">
        <h2 className="text-lg font-medium">Providers & credentials</h2>
        <div className="grid gap-4">
          {drafts?.map((d) => {
            const live = availabilityByName.get(d.provider_name);
            const isOllama = d.provider_name === "ollama";
            const isKeyed = KEYED_PROVIDERS.includes(d.provider_name);
            return (
              <div
                key={d.provider_name}
                className={`rounded-xl border p-5 transition-all ${
                  d.enabled
                    ? "border-emerald-700 bg-emerald-950/10"
                    : "border-neutral-800 bg-neutral-900/30"
                }`}
              >
                {/* Provider header */}
                <div className="flex items-center justify-between gap-3">
                  <label className="flex cursor-pointer items-center gap-3">
                    <div
                      className={`flex h-5 w-5 items-center justify-center rounded border-2 transition-colors ${
                        d.enabled
                          ? "border-emerald-500 bg-emerald-600"
                          : "border-neutral-600 bg-transparent"
                      }`}
                    >
                      {d.enabled && (
                        <svg xmlns="http://www.w3.org/2000/svg" className="h-3 w-3 text-white" viewBox="0 0 20 20" fill="currentColor">
                          <path fillRule="evenodd" d="M16.707 5.293a1 1 0 010 1.414l-8 8a1 1 0 01-1.414 0l-4-4a1 1 0 011.414-1.414L8 12.586l7.293-7.293a1 1 0 011.414 0z" clipRule="evenodd" />
                        </svg>
                      )}
                    </div>
                    <input
                      type="checkbox"
                      checked={d.enabled}
                      onChange={(e) => patchDraft(d.provider_name, { enabled: e.target.checked })}
                      className="sr-only"
                    />
                    <span className="text-base">{PROVIDER_ICONS[d.provider_name] || "🔌"}</span>
                    <span className="text-sm font-medium capitalize">{d.provider_name}</span>
                  </label>
                  <div className="flex items-center gap-2">
                    {d.enabled ? (
                      live?.available ? (
                        <span className="flex items-center gap-1.5 rounded-full bg-emerald-500/10 px-2.5 py-1 text-[10px] text-emerald-400 ring-1 ring-emerald-500/30">
                          <span className="h-1.5 w-1.5 rounded-full bg-emerald-500" />
                          {live.models.length} models
                        </span>
                      ) : (
                        <span className="flex items-center gap-1.5 rounded-full bg-amber-500/10 px-2.5 py-1 text-[10px] text-amber-400 ring-1 ring-amber-500/30">
                          <span className="h-1.5 w-1.5 rounded-full bg-amber-500" />
                          unreachable
                        </span>
                      )
                    ) : (
                      <span className="text-[10px] text-neutral-600">disabled</span>
                    )}
                  </div>
                </div>

                {/* Expanded config */}
                {d.enabled && (
                  <div className="mt-4 grid gap-4 sm:grid-cols-2">
                    {isKeyed && (
                      <div className="space-y-1">
                        <label className="text-xs text-neutral-500">API key</label>
                        <input
                          type="password"
                          value={d.api_key_input === CLEAR_SENTINEL ? "" : d.api_key_input}
                          placeholder={
                            d.has_api_key ? "•••••• stored (leave blank to keep)" : "Enter API key"
                          }
                          onChange={(e) =>
                            patchDraft(d.provider_name, { api_key_input: e.target.value })
                          }
                          className="w-full rounded-lg bg-neutral-950 px-3 py-2 text-sm outline-none ring-1 ring-neutral-800 transition-all focus:ring-2 focus:ring-emerald-600"
                        />
                        {d.has_api_key && (
                          <button
                            type="button"
                            onClick={() =>
                              patchDraft(d.provider_name, { api_key_input: CLEAR_SENTINEL })
                            }
                            className="text-xs text-red-400 hover:text-red-300"
                          >
                            Clear stored key
                          </button>
                        )}
                        {d.api_key_input === CLEAR_SENTINEL && (
                          <p className="text-xs text-red-400">Key will be cleared on save.</p>
                        )}
                      </div>
                    )}

                    {isKeyed && (
                      <div className="space-y-1">
                        <label className="text-xs text-neutral-500">Base URL (optional)</label>
                        <input
                          type="text"
                          value={d.base_url}
                          placeholder="Provider default"
                          onChange={(e) =>
                            patchDraft(d.provider_name, { base_url: e.target.value })
                          }
                          className="w-full rounded-lg bg-neutral-950 px-3 py-2 text-sm outline-none ring-1 ring-neutral-800 transition-all focus:ring-2 focus:ring-emerald-600"
                        />
                      </div>
                    )}

                    {isOllama && (
                      <>
                        <div className="space-y-1">
                          <label className="text-xs text-neutral-500">Mode</label>
                          <select
                            value={d.ollama_mode}
                            onChange={(e) =>
                              patchDraft(d.provider_name, {
                                ollama_mode: e.target.value as OllamaMode,
                              })
                            }
                            className="w-full rounded-lg bg-neutral-950 px-3 py-2 text-sm outline-none ring-1 ring-neutral-800 focus:ring-2 focus:ring-emerald-600"
                          >
                            <option value="localhost">localhost</option>
                            <option value="cloud">cloud</option>
                          </select>
                        </div>
                        <div className="space-y-1">
                          <label className="text-xs text-neutral-500">Local base URL</label>
                          <input
                            type="text"
                            value={d.ollama_local_base_url}
                            placeholder="http://localhost:11434"
                            onChange={(e) =>
                              patchDraft(d.provider_name, {
                                ollama_local_base_url: e.target.value,
                              })
                            }
                            className="w-full rounded-lg bg-neutral-950 px-3 py-2 text-sm outline-none ring-1 ring-neutral-800 focus:ring-2 focus:ring-emerald-600"
                          />
                        </div>
                        <div className="space-y-1">
                          <label className="text-xs text-neutral-500">Cloud base URL</label>
                          <input
                            type="text"
                            value={d.ollama_cloud_base_url}
                            placeholder="https://your-ollama-host"
                            onChange={(e) =>
                              patchDraft(d.provider_name, {
                                ollama_cloud_base_url: e.target.value,
                              })
                            }
                            className="w-full rounded-lg bg-neutral-950 px-3 py-2 text-sm outline-none ring-1 ring-neutral-800 focus:ring-2 focus:ring-emerald-600"
                          />
                        </div>
                      </>
                    )}
                  </div>
                )}
              </div>
            );
          })}
        </div>

        <button
          onClick={saveProviders}
          disabled={saving || !drafts}
          className="flex items-center gap-2 rounded-xl bg-emerald-600 px-5 py-2.5 text-sm font-medium transition-all hover:bg-emerald-500 hover:shadow-lg hover:shadow-emerald-600/20 disabled:opacity-50 disabled:shadow-none"
        >
          {saving ? (
            <>
              <div className="h-4 w-4 animate-spin rounded-full border-2 border-white border-t-transparent" />
              Saving...
            </>
          ) : (
            <>
              <svg xmlns="http://www.w3.org/2000/svg" className="h-4 w-4" viewBox="0 0 20 20" fill="currentColor">
                <path d="M7.707 10.293a1 1 0 10-1.414 1.414l3 3a1 1 0 001.414 0l3-3a1 1 0 00-1.414-1.414L11 11.586V6h5a2 2 0 012 2v7a2 2 0 01-2 2H4a2 2 0 01-2-2V8a2 2 0 012-2h5v5.586l-1.293-1.293z" />
              </svg>
              Save providers
            </>
          )}
        </button>
      </section>

      {/* Agent role model assignment */}
      <section className="space-y-4">
        <div className="flex items-center justify-between">
          <h2 className="text-lg font-medium">Agent role models</h2>
          <span className="text-xs text-neutral-500">
            Format: <code className="rounded bg-neutral-800 px-1 py-0.5 font-mono">provider:model</code>
          </span>
        </div>

        {!agents ? (
          <p className="text-sm text-neutral-500">Loading agents...</p>
        ) : (
          <>
            <div className="flex items-center gap-3">
              <label className="text-xs text-neutral-500" htmlFor="model-search">
                Search models
              </label>
              <input
                id="model-search"
                value={modelSearch}
                onChange={(e) => setModelSearch(e.target.value)}
                placeholder="Type provider:model (e.g. openrouter:llama) ..."
                className="w-full rounded-lg bg-neutral-950 px-3 py-2 text-sm outline-none ring-1 ring-neutral-800 transition-all focus:ring-2 focus:ring-emerald-600"
              />
              {modelSearch.trim() !== "" && (
                <button
                  type="button"
                  onClick={() => setModelSearch("")}
                  className="text-xs text-neutral-400 hover:text-neutral-200"
                >
                  Clear
                </button>
              )}
            </div>

            <div className="overflow-x-auto rounded-xl border border-neutral-800">
              <table className="min-w-full text-sm">
              <thead>
                <tr className="border-b border-neutral-800 bg-neutral-900/50">
                  <th className="px-4 py-3 text-left text-xs font-medium uppercase tracking-wide text-neutral-500">
                    Role
                  </th>
                  <th className="px-4 py-3 text-left text-xs font-medium uppercase tracking-wide text-neutral-500">
                    Current model
                  </th>
                  <th className="px-4 py-3 text-left text-xs font-medium uppercase tracking-wide text-neutral-500">
                    Assign
                  </th>
                </tr>
              </thead>
              <tbody>
                {agents
                  .slice()
                  .sort((a, b) => a.role.localeCompare(b.role))
                  .map((a, i) => {
                    const chosen = roleModelMap[a.role] ?? a.model;
                    const options = Array.from(new Set([chosen, ...filteredAvailableModelRefs]));
                    return (
                      <tr
                        key={a.id}
                        className={`border-b border-neutral-800 transition-colors hover:bg-neutral-900/30 ${
                          i === agents.length - 1 ? "border-b-0" : ""
                        }`}
                      >
                        <td className="px-4 py-3">
                          <div className="flex items-center gap-2">
                            <div className="flex h-6 w-6 items-center justify-center rounded-md bg-emerald-600/20 text-[10px] text-emerald-400">
                              {a.role.charAt(0).toUpperCase()}
                            </div>
                            <span className="font-medium capitalize">{a.role}</span>
                          </div>
                        </td>
                        <td className="px-4 py-3">
                          <code className="rounded bg-neutral-800 px-2 py-0.5 font-mono text-xs text-neutral-300">
                            {a.model}
                          </code>
                        </td>
                        <td className="px-4 py-3">
                          <select
                            value={chosen}
                            onChange={(e) =>
                              setRoleModelMap((prev) => ({ ...prev, [a.role]: e.target.value }))
                            }
                            className="w-full max-w-xs rounded-lg bg-neutral-950 px-3 py-2 text-sm outline-none ring-1 ring-neutral-800 focus:ring-2 focus:ring-emerald-600"
                          >
                            {options.map((ref) => (
                              <option key={ref} value={ref}>
                                {ref}
                              </option>
                            ))}
                          </select>
                        </td>
                      </tr>
                    );
                  })}
              </tbody>
              </table>
            </div>
          </>
        )}

        <div className="flex items-center gap-3">
          <button
            onClick={applyRoleModels}
            disabled={saving || !agents}
            className="flex items-center gap-2 rounded-xl bg-emerald-600 px-5 py-2.5 text-sm font-medium transition-all hover:bg-emerald-500 hover:shadow-lg hover:shadow-emerald-600/20 disabled:opacity-50 disabled:shadow-none"
          >
            {saving ? (
              <>
                <div className="h-4 w-4 animate-spin rounded-full border-2 border-white border-t-transparent" />
                Saving...
              </>
            ) : (
              <>
                <svg xmlns="http://www.w3.org/2000/svg" className="h-4 w-4" viewBox="0 0 20 20" fill="currentColor">
                  <path fillRule="evenodd" d="M16.707 5.293a1 1 0 010 1.414l-8 8a1 1 0 01-1.414 0l-4-4a1 1 0 011.414-1.414L8 12.586l7.293-7.293a1 1 0 011.414 0z" clipRule="evenodd" />
                </svg>
                Save role models
              </>
            )}
          </button>
          <Link
            href="/workspace"
            className="text-sm text-neutral-500 underline hover:text-neutral-300"
          >
            Go to workspace
          </Link>
        </div>
      </section>
    </div>
  );
}