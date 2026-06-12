import { useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { apiFetch } from "../api/rest";

export function ReviewQueue() {
  const qc = useQueryClient();
  const [notes, setNotes] = useState({});

  const pending = useQuery({
    queryKey: ["feedback-pending"],
    queryFn: () => apiFetch("/feedback/pending"),
    refetchInterval: 8_000,
  });

  const submit = useMutation({
    mutationFn: (payload) =>
      apiFetch("/feedback/submit", { method: "POST", body: JSON.stringify(payload) }),
    onSuccess: (_data, variables) => {
      setNotes((prev) => {
        const next = { ...prev };
        delete next[variables.decision_id];
        return next;
      });
      qc.invalidateQueries({ queryKey: ["feedback-pending"] });
    },
  });

  const items = pending.data?.pending || [];

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-xl font-semibold">Review Queue</h1>
        <p className="mt-1 text-sm dark:text-slate-400 light:text-slate-600">
          Approve, reject, or annotate flagged decisions.
        </p>
      </div>

      {pending.isLoading && <p className="text-sm dark:text-slate-400">Loading queue…</p>}
      {pending.isError && <p className="text-sm text-rose-400">{pending.error.message}</p>}
      {submit.isError && <p className="text-sm text-rose-400">Submit failed: {submit.error.message}</p>}

      {items.length === 0 && pending.isSuccess && (
        <p className="text-sm dark:text-slate-500">No pending reviews.</p>
      )}

      <ul className="space-y-4">
        {items.map((item) => (
          <li
            key={item.feedback_id || item.decision_id}
            className="rounded-lg border dark:border-slate-800 light:border-slate-200 p-4"
          >
            <div className="font-mono text-xs dark:text-slate-400">{item.decision_id}</div>
            <div className="mt-2 text-sm">{item.note || "—"}</div>
            <label className="mt-3 block text-sm">
              Review note
              <input
                className="mt-1 w-full rounded border dark:border-slate-700 light:border-slate-300 dark:bg-slate-900 light:bg-white px-3 py-2"
                value={notes[item.decision_id] || ""}
                onChange={(e) =>
                  setNotes((prev) => ({ ...prev, [item.decision_id]: e.target.value }))
                }
              />
            </label>
            <div className="mt-3 flex gap-2">
              {["APPROVE", "REJECT", "FLAG"].map((action) => (
                <button
                  key={action}
                  type="button"
                  disabled={submit.isPending}
                  onClick={() =>
                    submit.mutate({
                      decision_id: item.decision_id,
                      action,
                      note: notes[item.decision_id] || "",
                      reviewer: "dashboard",
                    })
                  }
                  className="rounded border dark:border-slate-600 light:border-slate-300 px-3 py-1 text-xs dark:hover:bg-slate-800 light:hover:bg-slate-100 disabled:opacity-50"
                >
                  {action}
                </button>
              ))}
            </div>
          </li>
        ))}
      </ul>
    </div>
  );
}
