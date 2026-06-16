"use client";

import { useEffect, useMemo, useState } from "react";
import Link from "next/link";
import { api, type Agent, type ProviderInfo } from "@/lib/api";

type RoleToModelRef = Record<string, string>; // role -> "<provider>:<model>"

type PersistedConfig = {
  selectedProviders: string[]; // provider names
  roleModelMap: RoleToModelRef;
};

const STORAGE_KEY = "ads.llmConfig";

function safeParse<T>(raw: string | null): T | null {
  if (!raw) return null;
  try {
    return JSON.parse(raw) as T;
  } catch {
    return null;
  }
}

export default function LlmConfigPage() {
  const [providers, setProviders] = useState<ProviderInfo[] | null>(null);
  const [agents, setAgents] = useState<Agent[] | null>(null);
  const [loading, setLoading] = useState(true);
  const [err, setErr] = useState<string | null>(null);

  const [selectedProviders, setSelectedProviders] = useState<string[]>([]);
  const [roleModelMap, setRoleModelMap] = useState<RoleToModelRef>({});

  useEffect(() => {
    const persisted = safeParse<PersistedConfig>(localStorage.getItem(STORAGE_KEY));
    if (persisted?.selectedProviders) setSelectedProviders(persisted.selectedProviders);
    if (persisted?.roleModelMap) setRoleModelMap(persisted.roleModelMap);
  }, []);

  useEffect(() => {
    let cancelled = false;

    async function load() {
      setLoading(true);
      setErr(null);
      try {
        const [p, a] = await Promise.all([api.providers(), api.agents()]);
        if (cancelled) return;
        setProviders(p);
        setAgents(a);

        // Seed roleModelMap with existing agent models if empty.
        if (Object.keys(roleModelMap).length === 0) {
          const initial: RoleToModelRef = {};
          for (const ag of a) initial[ag.role] = ag.model;
          setRoleModelMap(initial);
        }
      } catch (e) {
        if (cancelled) return;
        setErr(e instanceof Error ? e.message : String(e));
      } finally {
        if (!cancelled) setLoading(false);
      }
    }

    load();
    return () => {
      cancelled = true;
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  useEffect(() => {
    const next: PersistedConfig = { selectedProviders, roleModelMap };
    localStorage.setItem(STORAGE_KEY, JSON.stringify(next));
  }, [selectedProviders, roleModelMap]);

  const selectedProviderInfos = useMemo(() => {
    if (!providers) return [];
    const set = new Set(selectedProviders);
    return providers.filter((p) => set.has(p.name));
  }, [providers, selectedProviders]);

  const allSelectedModelRefs = useMemo(() => {
    // Build model refs in "<provider>:<model>" format.
    const refs: string[] = [];
    for (const p of selectedProviderInfos) {
      for (const m of p.models) refs.push(`${p.name}:${m}`);
    }
    // De-dupe but keep stable ordering.
    return Array.from(new Set(refs));
  }, [selectedProviderInfos]);

  function toggleProvider(name: string) {
    setSelectedProviders((prev) => {
      const set = new Set(prev);
      if (set.has(name)) set.delete(name);
      else set.add(name);
      return Array.from(set);
    });
  }

  async function applyToAgentRoles() {
    if (!agents) return;

    if (selectedProviders.length === 0) {
      setErr("Select at least one provider to apply models.");
      return;
    }
    if (allSelectedModelRefs.length === 0) {
      setErr("Selected providers do not report any available models.");
      return;
    }

    setErr(null);
    setLoading(true);
    try {
      // Update each agent role with roleModelMap[role] or fallback.
      for (const a of agents) {
        const chosen = roleModelMap[a.role] ?? a.model;
        if (!chosen) continue;
        await api.setAgentModel(a.id, chosen);
      }
      // Refresh agents to reflect saved models.
      const updatedAgents = await api.agents();
      setAgents(updatedAgents);
    } catch (e) {
      setErr(e instanceof Error ? e.message : String(e));
    } finally {
      setLoading(false);
    }
  }

  if (loading && !providers) {
    return (
      <div className="space-y-2">
        <h1 className="text-2xl font-semibold">LLM Configuration</h1>
        <p className="text-sm text-neutral-400">Loading providers…</p>
      </div>
    );
  }

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-semibold">LLM Configuration</h1>
        <p className="text-sm text-neutral-400">
          Select multiple providers, pick models, then apply those choices to agent roles.
        </p>
        <p className="mt-2 text-sm text-neutral-400">
          Next: start a workspace flow (Chat / Agents) to use the configured models.
        </p>
      </div>

      {err ? (
        <div className="rounded-md border border-rose-500/40 bg-rose-500/10 p-3 text-sm text-rose-200">
          {err}
        </div>
      ) : null}

      {!providers ? null : (
        <section className="space-y-3">
          <h2 className="text-lg font-medium">Providers</h2>
          <div className="grid gap-3 sm:grid-cols-2">
            {providers.map((p) => {
              const checked = selectedProviders.includes(p.name);
              const disabled = !p.available;
              return (
                <label
                  key={p.name}
                  className={`flex items-start justify-between gap-3 rounded-lg border p-3 ${
                    checked ? "border-emerald-400/60" : "border-neutral-800"
                  } ${disabled ? "opacity-60" : ""}`}
                >
                  <div className="space-y-1">
                    <div className="flex items-center gap-2">
                      <input
                        type="checkbox"
                        checked={checked}
                        disabled={disabled}
                        onChange={() => toggleProvider(p.name)}
                      />
                      <span className="font-medium">{p.name}</span>
                    </div>
                    <div className="text-xs text-neutral-400">
                      {p.available ? `${p.models.length} models available` : "Unavailable"}
                    </div>
                  </div>
                  <div className="text-xs text-neutral-400 text-right">
                    {checked ? "Selected" : "Not selected"}
                  </div>
                </label>
              );
            })}
          </div>
        </section>
      )}

      <section className="space-y-3">
        <div className="flex items-baseline justify-between gap-4">
          <h2 className="text-lg font-medium">Assign model per agent role</h2>
          <div className="text-xs text-neutral-400">
            Model refs are in the form <span className="font-mono">{`<provider>:<model>`}</span>
          </div>
        </div>

        {!agents ? null : (
          <div className="overflow-x-auto">
            <table className="min-w-[520px] w-full text-sm">
              <thead>
                <tr className="text-left text-xs text-neutral-400">
                  <th className="py-2 pr-3">Role</th>
                  <th className="py-2 pr-3">Current</th>
                  <th className="py-2">Choose (from selected providers)</th>
                </tr>
              </thead>
              <tbody>
                {agents
                  .slice()
                  .sort((a, b) => a.role.localeCompare(b.role))
                  .map((a) => {
                    const chosen = roleModelMap[a.role] ?? a.model;
                    return (
                      <tr key={a.id} className="border-t border-neutral-800">
                        <td className="py-2 pr-3 font-medium">{a.role}</td>
                        <td className="py-2 pr-3">
                          <span className="font-mono text-xs text-neutral-300">{a.model}</span>
                        </td>
                        <td className="py-2">
                          <select
                            className="w-full rounded-md border border-neutral-800 bg-neutral-950 px-2 py-1 text-sm"
                            value={chosen}
                            onChange={(e) => {
                              const v = e.target.value;
                              setRoleModelMap((prev) => ({ ...prev, [a.role]: v }));
                            }}
                            disabled={allSelectedModelRefs.length === 0}
                          >
                            {allSelectedModelRefs.length === 0 ? (
                              <option value={chosen}>Select provider(s) to enable models</option>
                            ) : (
                              allSelectedModelRefs.map((ref) => (
                                <option key={ref} value={ref}>
                                  {ref}
                                </option>
                              ))
                            )}
                          </select>
                        </td>
                      </tr>
                    );
                  })}
              </tbody>
            </table>
          </div>
        )}

        <div className="flex flex-wrap items-center gap-3">
          <button
            onClick={applyToAgentRoles}
            disabled={loading || !agents}
            className="rounded-md bg-emerald-500/90 px-4 py-2 text-sm font-medium text-black disabled:opacity-60"
          >
            Apply to all agent roles
          </button>

          <Link
            href="/workspace"
            className="text-sm underline text-emerald-300"
          >
            Go to Workspace
          </Link>
        </div>

        <div className="text-xs text-neutral-500">
          Note: This is frontend-scaffold persistence. Persisted selections are stored in your browser
          (localStorage) and applied to agent roles via existing backend endpoints.
        </div>
      </section>
    </div>
  );
}
