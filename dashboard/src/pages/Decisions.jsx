import { useState } from "react";
import { useMutation } from "@tanstack/react-query";
import { apiFetch } from "../api/rest";

export function Decisions() {
  const [symbol, setSymbol] = useState("BTCUSD");
  const [price, setPrice] = useState("42000");
  const [volume, setVolume] = useState("1.0");
  const [lastDecisionId, setLastDecisionId] = useState("");
  const [audit, setAudit] = useState(null);
  const [error, setError] = useState("");

  const ingest = useMutation({
    mutationFn: async () => {
      const body = {
        symbol,
        price: Number(price),
        volume: Number(volume),
        timestamp: new Date().toISOString(),
      };
      return apiFetch("/ingest", { method: "POST", body: JSON.stringify(body) });
    },
    onSuccess: async (data) => {
      setError("");
      setLastDecisionId(data.decision_id);
      const chain = await apiFetch(`/audit/decision/${data.decision_id}`);
      setAudit(chain);
    },
    onError: (err) => setError(err.message),
  });

  const bootstrap = useMutation({
    mutationFn: () => apiFetch("/bootstrap-demo", { method: "POST" }),
    onSuccess: async (data) => {
      setError("");
      setLastDecisionId(data.decision_id);
      const chain = await apiFetch(`/audit/decision/${data.decision_id}`);
      setAudit(chain);
    },
    onError: (err) => setError(err.message),
  });

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-xl font-semibold">Decisions</h1>
        <p className="mt-1 text-sm dark:text-slate-400 light:text-slate-600">
          Submit a demo market event or run bootstrap-demo, then inspect the audit chain.
        </p>
      </div>

      <form
        className="grid gap-4 rounded-lg border dark:border-slate-800 light:border-slate-200 p-4 sm:grid-cols-3"
        onSubmit={(e) => {
          e.preventDefault();
          ingest.mutate();
        }}
      >
        <label className="text-sm">
          Symbol
          <input
            className="mt-1 w-full rounded border dark:border-slate-700 light:border-slate-300 dark:bg-slate-900 light:bg-white px-3 py-2"
            value={symbol}
            onChange={(e) => setSymbol(e.target.value)}
          />
        </label>
        <label className="text-sm">
          Price
          <input
            className="mt-1 w-full rounded border dark:border-slate-700 light:border-slate-300 dark:bg-slate-900 light:bg-white px-3 py-2"
            value={price}
            onChange={(e) => setPrice(e.target.value)}
          />
        </label>
        <label className="text-sm">
          Volume
          <input
            className="mt-1 w-full rounded border dark:border-slate-700 light:border-slate-300 dark:bg-slate-900 light:bg-white px-3 py-2"
            value={volume}
            onChange={(e) => setVolume(e.target.value)}
          />
        </label>
        <div className="flex flex-wrap gap-2 sm:col-span-3">
          <button
            type="submit"
            disabled={ingest.isPending}
            className="rounded bg-sky-600 px-4 py-2 text-sm font-medium text-white hover:bg-sky-500 disabled:opacity-50"
          >
            {ingest.isPending ? "Ingesting…" : "Ingest event"}
          </button>
          <button
            type="button"
            disabled={bootstrap.isPending}
            onClick={() => bootstrap.mutate()}
            className="rounded border dark:border-slate-600 light:border-slate-300 px-4 py-2 text-sm dark:hover:bg-slate-800 light:hover:bg-slate-100 disabled:opacity-50"
          >
            Bootstrap demo
          </button>
        </div>
      </form>

      {error && <p className="text-sm text-rose-400">{error}</p>}

      {lastDecisionId && (
        <div className="rounded-lg border dark:border-slate-800 light:border-slate-200 p-4">
          <div className="text-sm font-medium">Latest decision</div>
          <div className="mt-1 font-mono text-xs dark:text-slate-400">{lastDecisionId}</div>
        </div>
      )}

      {audit && (
        <pre className="overflow-x-auto rounded-lg border dark:border-slate-800 light:border-slate-200 dark:bg-slate-900/50 light:bg-slate-100 p-4 text-xs">
          {JSON.stringify(audit, null, 2)}
        </pre>
      )}
    </div>
  );
}
