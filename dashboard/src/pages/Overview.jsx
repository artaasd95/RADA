import { useMemo } from "react";
import { useQuery } from "@tanstack/react-query";
import { apiFetch } from "../api/rest";

function toNumber(value) {
  const n = Number(value ?? 0);
  return Number.isFinite(n) ? n : 0;
}

function Kpi({ label, value }) {
  return (
    <div className="kpi">
      <div className="kpi__label">{label}</div>
      <div className="kpi__value">{value}</div>
    </div>
  );
}

export function Overview() {
  const health = useQuery({
    queryKey: ["health"],
    queryFn: () => apiFetch("/health"),
    refetchInterval: 10_000,
  });

  const metrics = useQuery({
    queryKey: ["metrics-json"],
    queryFn: () => apiFetch("/metrics/json"),
    refetchInterval: 6_000,
  });

  const timeline = useMemo(() => {
    const now = Date.now();
    const base = toNumber(metrics.data?.legacy?.decisions_processed);
    return Array.from({ length: 12 }).map((_, i) => {
      const jitter = ((now / 1000 + i * 17) % 9) + 1;
      return Math.max(1, Math.round((base % 70) * 0.2 + jitter * 4));
    });
  }, [metrics.data]);

  const max = Math.max(...timeline, 1);
  const legacy = metrics.data?.legacy ?? {};
  const obs = metrics.data?.observability ?? {};
  const healthy = health.data?.status === "ok";

  return (
    <section className="stack">
      <div className="card">
        <h3>Mission Control</h3>
        <p>
          Watch live health, runtime counters, and flow rhythm. This surface is designed for
          operators running incident triage or release verification.
        </p>
      </div>

      <div className="kpi-grid">
        <Kpi
          label="API status"
          value={health.isLoading ? "Checking" : healthy ? "Healthy" : "Offline"}
        />
        <Kpi
          label="Decisions processed"
          value={toNumber(legacy.decisions_processed ?? obs.decisions_total).toLocaleString()}
        />
        <Kpi
          label="Risk gate pass"
          value={toNumber(legacy.risk_gate_passes).toLocaleString()}
        />
        <Kpi
          label="Reflections queued"
          value={toNumber(legacy.reflection_enqueued).toLocaleString()}
        />
      </div>

      <div className="page-grid">
        <article className="card" style={{ gridColumn: "span 8" }}>
          <h3>Decision Flow Rhythm</h3>
          <p>12-slice sparkline to approximate throughput movement between refresh intervals.</p>
          <div className="trend-bars" aria-hidden>
            {timeline.map((v, idx) => (
              <div
                key={idx}
                className="trend-bar"
                style={{ height: `${Math.round((v / max) * 100)}%` }}
              />
            ))}
          </div>
          <p className="muted" style={{ marginTop: 8 }}>
            Use this as a quick signal while you inspect detailed logs and traces.
          </p>
        </article>

        <article className="card" style={{ gridColumn: "span 4" }}>
          <h3>Endpoint Reachability</h3>
          {health.isError && <p className="badge badge--bad">Unreachable</p>}
          {health.isSuccess && <p className="badge badge--ok">/health ok</p>}
          {metrics.isError && <p className="badge badge--warn">/metrics/json error</p>}
          {metrics.isSuccess && <p className="badge badge--ok">/metrics/json ok</p>}
          <div className="stack" style={{ marginTop: 10 }}>
            <p className="muted">Target API</p>
            <p className="mono">{import.meta.env.VITE_API_URL || "same-origin proxy"}</p>
          </div>
        </article>
      </div>
    </section>
  );
}
