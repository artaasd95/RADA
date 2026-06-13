import { useMemo, useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { apiFetch } from "../api/rest";

export function ReviewQueue() {
  const queryClient = useQueryClient();
  const [query, setQuery] = useState("");
  const [notes, setNotes] = useState({});

  const pending = useQuery({
    queryKey: ["feedback-pending"],
    queryFn: () => apiFetch("/feedback/pending"),
    refetchInterval: 8_000,
  });

  const submit = useMutation({
    mutationFn: (payload) =>
      apiFetch("/feedback/submit", { method: "POST", body: JSON.stringify(payload) }),
    onSuccess: (_data, vars) => {
      setNotes((prev) => {
        const next = { ...prev };
        delete next[vars.decision_id];
        return next;
      });
      queryClient.invalidateQueries({ queryKey: ["feedback-pending"] });
    },
  });

  const items = pending.data?.pending || [];
  const filtered = useMemo(
    () => items.filter((item) => item.decision_id.toLowerCase().includes(query.toLowerCase())),
    [items, query],
  );

  const send = (item, action) => {
    submit.mutate({
      decision_id: item.decision_id,
      action,
      note: notes[item.decision_id] || `${action} from React console`,
      reviewer: "react-dashboard",
    });
  };

  return (
    <section className="stack">
      <div className="card">
        <h3>Review Desk</h3>
        <p>
          Triage flagged decisions, capture reviewer notes, and send explicit APPROVE/REJECT/FLAG
          actions back to the API.
        </p>
      </div>

      <div className="card">
        <label>
          Filter by decision id
          <input
            value={query}
            onChange={(event) => setQuery(event.target.value)}
            placeholder="Search queue"
          />
        </label>
      </div>

      {pending.isLoading && <div className="empty">Loading pending queue...</div>}
      {pending.isError && <div className="empty">Queue unavailable: {pending.error.message}</div>}
      {submit.isError && <div className="empty">Submit failed: {submit.error.message}</div>}

      {pending.isSuccess && filtered.length === 0 && <div className="empty">No pending items.</div>}

      <div className="stack">
        {filtered.map((item) => (
          <article className="card" key={item.feedback_id || item.decision_id}>
            <div className="stack">
              <p className="mono">{item.decision_id}</p>
              <p>{item.note || "No reviewer note yet."}</p>
              <p className="muted">Action requested: {item.action}</p>
              <label>
                Reviewer note
                <textarea
                  value={notes[item.decision_id] || ""}
                  onChange={(event) =>
                    setNotes((prev) => ({ ...prev, [item.decision_id]: event.target.value }))
                  }
                />
              </label>
              <div className="btn-row">
                <button
                  type="button"
                  className="btn-primary"
                  disabled={submit.isPending}
                  onClick={() => send(item, "APPROVE")}
                >
                  Approve
                </button>
                <button
                  type="button"
                  className="btn-danger"
                  disabled={submit.isPending}
                  onClick={() => send(item, "REJECT")}
                >
                  Reject
                </button>
                <button
                  type="button"
                  className="btn-secondary"
                  disabled={submit.isPending}
                  onClick={() => send(item, "FLAG")}
                >
                  Re-flag
                </button>
              </div>
            </div>
          </article>
        ))}
      </div>
    </section>
  );
}
