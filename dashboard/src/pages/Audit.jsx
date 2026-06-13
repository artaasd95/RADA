import { useState } from "react";
import { apiFetch, apiUrl } from "../api/rest";

export function Audit() {
  const [decisionId, setDecisionId] = useState("");
  const [from, setFrom] = useState("");
  const [to, setTo] = useState("");
  const [limit, setLimit] = useState("1000");
  const [error, setError] = useState("");
  const [result, setResult] = useState(null);

  const fetchDecisionAudit = async () => {
    if (!decisionId.trim()) {
      setError("Decision id is required");
      return;
    }
    try {
      const data = await apiFetch(`/audit/decision/${decisionId.trim()}`);
      setResult(data);
      setError("");
    } catch (err) {
      setError(err.message);
      setResult(null);
    }
  };

  const downloadExport = () => {
    const params = new URLSearchParams();
    if (from) params.set("from_", from);
    if (to) params.set("to", to);
    if (limit) params.set("limit", String(Math.max(1, Number(limit) || 1000)));
    const qs = params.toString();
    const target = apiUrl(`/audit/export${qs ? `?${qs}` : ""}`);
    window.open(target, "_blank", "noopener,noreferrer");
  };

  return (
    <section className="stack">
      <div className="card">
        <h3>Audit Vault</h3>
        <p>
          Pull complete audit chains for one decision and export NDJSON batches for incident review,
          governance reports, or offline analysis.
        </p>
      </div>

      <div className="page-grid">
        <article className="card" style={{ gridColumn: "span 7" }}>
          <h3>Decision Chain Lookup</h3>
          <label>
            Decision id
            <input
              value={decisionId}
              onChange={(event) => setDecisionId(event.target.value)}
              placeholder="Paste decision_id"
            />
          </label>
          <div className="btn-row">
            <button type="button" className="btn-primary" onClick={fetchDecisionAudit}>
              Fetch Audit Chain
            </button>
          </div>
        </article>

        <article className="card" style={{ gridColumn: "span 5" }}>
          <h3>NDJSON Export</h3>
          <div className="stack">
            <label>
              From (ISO8601)
              <input
                value={from}
                onChange={(event) => setFrom(event.target.value)}
                placeholder="2026-06-01T00:00:00Z"
              />
            </label>
            <label>
              To (ISO8601)
              <input
                value={to}
                onChange={(event) => setTo(event.target.value)}
                placeholder="2026-06-12T23:59:59Z"
              />
            </label>
            <label>
              Limit
              <input value={limit} onChange={(event) => setLimit(event.target.value)} />
            </label>
          </div>
          <div className="btn-row">
            <button type="button" className="btn-secondary" onClick={downloadExport}>
              Download Export
            </button>
          </div>
        </article>
      </div>

      {error && <div className="empty">{error}</div>}

      {result && (
        <article className="card">
          <h3>Audit Events ({result.events?.length || 0})</h3>
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
                {(result.events || []).map((event) => (
                  <tr key={event.event_id}>
                    <td>{event.event_type}</td>
                    <td className="mono">{event.timestamp}</td>
                    <td className="mono">{event.event_id.slice(0, 16)}...</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </article>
      )}
    </section>
  );
}
