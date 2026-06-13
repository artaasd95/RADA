export const THEME_STORAGE_KEY = "rada_theme";

/** @returns {"dark" | "light"} */
export function getStoredTheme() {
  const v = localStorage.getItem(THEME_STORAGE_KEY);
  return v === "dark" ? "dark" : "light";
}

/** @param {"dark" | "light"} mode */
export function applyTheme(mode) {
  const root = document.documentElement;
  root.classList.remove("dark", "light");
  root.classList.add(mode === "light" ? "light" : "dark");
  localStorage.setItem(THEME_STORAGE_KEY, mode === "light" ? "light" : "dark");
}

export function initTheme() {
  applyTheme(getStoredTheme());
}

/** @returns {"dark" | "light"} */
export function cycleTheme() {
  const next = getStoredTheme() === "light" ? "dark" : "light";
  applyTheme(next);
  return next;
}
