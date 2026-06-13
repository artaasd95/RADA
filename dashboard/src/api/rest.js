const base = () => (import.meta.env.VITE_API_URL || "").replace(/\/$/, "");
const apiKey = import.meta.env.VITE_API_KEY || "";

export function apiUrl(path) {
  const p = path.startsWith("/") ? path : `/${path}`;
  return `${base()}${p}`;
}

/** @param {string} path @param {RequestInit} [init] */
export async function apiFetch(path, init = {}) {
  const headers = new Headers(init.headers);
  if (apiKey && !headers.has("X-API-Key")) {
    headers.set("X-API-Key", apiKey);
  }
  if (!headers.has("Content-Type") && init.body) {
    headers.set("Content-Type", "application/json");
  }
  const res = await fetch(apiUrl(path), { ...init, headers });
  if (!res.ok) {
    const text = await res.text();
    throw new Error(text || res.statusText);
  }
  if (res.status === 204) return undefined;
  const ct = res.headers.get("content-type") || "";
  if (ct.includes("application/json")) return res.json();
  return res.text();
}
