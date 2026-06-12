import { useQuery } from "@tanstack/react-query";
import { apiFetch } from "../api/rest";

function MetricCard({ label, value }) {
  return (
    <div className="rounded-lg border dark:border-slate-800 light:border-slate-200 dark:bg-slate-900/50 light:bg-white p-4">
      <div className="text-xs uppercase tracking-wide dark:text-slate-500 light:text-slate-500">{label}</div>
      <div className="mt-1 text-2xl font-semibold">{value}</div>
    </div>
  );
}

export function Overview() {
  const health = useQuery({
    queryKey: ["health"],
    queryFn: () => apiFetch("/health"),
    refetchInterval: 15_000,
  });

  const metrics = useQuery({
    queryKey: ["metrics-json"],
    queryFn: () => apiFetch("/metrics/json"),
    refetchInterval: 10_000,
  });

  const legacy = metrics.data?.legacy || {};
  const obs = metrics.data?.observability || {};

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-xl font-semibold">Overview</h1>
        <p className="mt-1 text-sm dark:text-slate-400 light:text-slate-600">
          API health and in-process decision metrics.
        </p>
      </div>

      <div className="rounded-lg border dark:border-slate-800 light:border-slate-200 p-4">
        <div className="text-sm font-medium">API status</div>
        {health.isLoading && <p className="mt-2 text-sm dark:text-slate-400">Checking…</p>}
        {health.isError && (
          <p className="mt-2 text-sm text-rose-400">Unreachable: {health.error.message}</p>
        )}
        {health.isSuccess && (
          <p className="mt-2 text-sm text-emerald-400">Healthy — {health.data.status}</p>
        )}
      </div>

      <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
        <MetricCard label="Decisions processed" value={legacy.decisions_processed ?? obs.decisions_total ?? "—"} />
        <MetricCard label="Risk gate passes" value={legacy.risk_gate_passes ?? "—"} />
        <MetricCard label="Reflection queued" value={legacy.reflection_enqueued ?? "—"} />
      </div>
    </div>
  );
}
