import { useState } from "react";
import { apiUrl } from "../api/rest";

export function Audit() {
  const [from, setFrom] = useState("");
  const [to, setTo] = useState("");

  function download() {
    const params = new URLSearchParams();
    if (from) params.set("from_", from);
    if (to) params.set("to", to);
    const qs = params.toString();
    const url = apiUrl(`/audit/export${qs ? `?${qs}` : ""}`);
    window.open(url, "_blank", "noopener,noreferrer");
  }

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-xl font-semibold">Audit export</h1>
        <p className="mt-1 text-sm dark:text-slate-400 light:text-slate-600">
          Download NDJSON audit events for a time range (ISO-8601, optional).
        </p>
      </div>

      <div className="grid gap-4 rounded-lg border dark:border-slate-800 light:border-slate-200 p-4 sm:grid-cols-2">
        <label className="text-sm">
          From (ISO)
          <input
            className="mt-1 w-full rounded border dark:border-slate-700 light:border-slate-300 dark:bg-slate-900 light:bg-white px-3 py-2"
            placeholder="2026-06-01T00:00:00Z"
            value={from}
            onChange={(e) => setFrom(e.target.value)}
          />
        </label>
        <label className="text-sm">
          To (ISO)
          <input
            className="mt-1 w-full rounded border dark:border-slate-700 light:border-slate-300 dark:bg-slate-900 light:bg-white px-3 py-2"
            placeholder="2026-06-12T23:59:59Z"
            value={to}
            onChange={(e) => setTo(e.target.value)}
          />
        </label>
        <button
          type="button"
          onClick={download}
          className="rounded bg-sky-600 px-4 py-2 text-sm font-medium text-white hover:bg-sky-500 sm:col-span-2 sm:w-fit"
        >
          Download NDJSON
        </button>
      </div>
    </div>
  );
}
