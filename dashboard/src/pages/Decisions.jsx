import { useMemo, useState } from "react";
import { useMutation } from "@tanstack/react-query";
import { apiFetch } from "../api/rest";

function parsePositiveNumber(value, field) {
  const parsed = Number(value);
  if (!Number.isFinite(parsed) || parsed <= 0) {
    throw new Error(`${field} must be a positive number`);
  }
  return parsed;
}

function findDirection(events) {
  for (const event of events || []) {
    const direction = event?.payload_after?.proposed_action?.direction;
    if (direction) {
      return direction;
    }
  }
  return "UNKNOWN";
}

export function Decisions() {
  const [symbol, setSymbol] = useState("BTCUSD");
  const [price, setPrice] = useState("62000");
  const [volume, setVolume] = useState("1.0");
  const [error, setError] = useState("");
  const [audit, setAudit] = useState(null);
  const [recent, setRecent] = useState([]);

  const direction = useMemo(() => findDirection(audit?.events), [audit]);

  const loadAudit = async (decisionId) => {
    const chain = await apiFetch(`/audit/decision/${decisionId}`);
    setAudit(chain);
  };

  const ingest = useMutation({
    mutationFn: async () => {
      const body = {
        symbol,
        price: parsePositiveNumber(price, "Price"),
        volume: parsePositiveNumber(volume, "Volume"),
        timestamp: new Date().toISOString(),
      };
      return apiFetch("/ingest", { method: "POST", body: JSON.stringify(body) });
    },
    onSuccess: async (data) => {
      setError("");
      await loadAudit(data.decision_id);
      setRecent((prev) => [
        {
          decision_id: data.decision_id,
          symbol,
          direction: data.direction,
          flagged: data.flagged,
          timestamp: new Date().toISOString(),
        },
        ...prev,
      ].slice(0, 20));
    },
    onError: (err) => setError(err.message),
  });

  const bootstrap = useMutation({
    mutationFn: () => apiFetch("/bootstrap-demo", { method: "POST" }),
    onSuccess: async (data) => {
      setError("");
      await loadAudit(data.decision_id);
      setRecent((prev) => [
        {
          decision_id: data.decision_id,
          symbol: "SYNTH",
          direction: "UNKNOWN",
          flagged: false,
          timestamp: new Date().toISOString(),
        },
        ...prev,
      ].slice(0, 20));
    },
    onError: (err) => setError(err.message),
  });

  return (
    <section className="stack">
      <div className="card">
        <h3>Decision Studio</h3>
        <p>
          Simulate market events, trigger decisions, and inspect the resulting audit chain and
          direction metadata in one place.
        </p>
      </div>

      <div className="card">
        <h3>Ingest Event</h3>
        <form
          className="form-grid"
          onSubmit={(event) => {
            event.preventDefault();
            ingest.mutate();
          }}
        >
          <label>
            Symbol
            <input value={symbol} onChange={(event) => setSymbol(event.target.value.toUpperCase())} />
          </label>
          <label>
            Price
            <input value={price} onChange={(event) => setPrice(event.target.value)} />
          </label>
          <label>
            Volume
            <input value={volume} onChange={(event) => setVolume(event.target.value)} />
          </label>
        </form>

        <div className="btn-row">
          <button type="button" className="btn-primary" onClick={() => ingest.mutate()} disabled={ingest.isPending}>
            {ingest.isPending ? "Ingesting..." : "Run Ingest"}
          </button>
          <button type="button" className="btn-secondary" onClick={() => bootstrap.mutate()} disabled={bootstrap.isPending}>
            {bootstrap.isPending ? "Running..." : "Bootstrap Demo"}
          </button>
        </div>

        {error && <p className="badge badge--bad">{error}</p>}
      </div>

      <div className="page-grid">
        <article className="card" style={{ gridColumn: "span 5" }}>
          <h3>Recent Decisions</h3>
          {recent.length === 0 ? (
            <div className="empty">No decisions yet. Start with Run Ingest.</div>
          ) : (
            <div className="table-wrap">
              <table>
                <thead>
                  <tr>
                    <th>Decision</th>
                    <th>Symbol</th>
                    <th>Direction</th>
                    <th>Flagged</th>
                  </tr>
                </thead>
                <tbody>
                  {recent.map((item) => (
                    <tr key={item.decision_id}>
                      <td className="mono">{item.decision_id.slice(0, 12)}...</td>
                      <td>{item.symbol}</td>
                      <td>{item.direction}</td>
                      <td>
                        <span className={item.flagged ? "badge badge--warn" : "badge badge--ok"}>
                          {item.flagged ? "flag" : "clean"}
                        </span>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </article>

        <article className="card" style={{ gridColumn: "span 7" }}>
          <h3>Audit Inspector</h3>
          {!audit ? (
            <div className="empty">Run an action and the latest audit chain will appear here.</div>
          ) : (
            <div className="stack">
              <p className="mono">decision_id: {audit.decision_id}</p>
              <p>
                inferred direction: <span className="badge badge--warn">{direction}</span>
              </p>
              <div className="table-wrap">
                <table>
                  <thead>
                    <tr>
                      <th>Event Type</th>
                      <th>Timestamp</th>
                      <th>Event ID</th>
                    </tr>
                  </thead>
                  <tbody>
                    {(audit.events || []).map((event) => (
                      <tr key={event.event_id}>
                        <td>{event.event_type}</td>
                        <td className="mono">{event.timestamp}</td>
                        <td className="mono">{event.event_id.slice(0, 12)}...</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </div>
          )}
        </article>
      </div>
    </section>
  );
}
