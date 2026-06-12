import { useState } from "react";
import { Link, Navigate, Route, Routes, useLocation } from "react-router-dom";
import { Overview } from "./pages/Overview";
import { Decisions } from "./pages/Decisions";
import { ReviewQueue } from "./pages/ReviewQueue";
import { Audit } from "./pages/Audit";
import { cycleTheme, getStoredTheme } from "./theme";

const links = [
  { to: "/", label: "Overview" },
  { to: "/decisions", label: "Decisions" },
  { to: "/review", label: "Review Queue" },
  { to: "/audit", label: "Audit" },
];

function Nav({ theme, onToggleTheme }) {
  const loc = useLocation();
  return (
    <nav className="flex flex-wrap items-center gap-4 border-b dark:border-slate-800 light:border-slate-200 dark:bg-slate-900/80 light:bg-white/90 px-6 py-3 text-sm backdrop-blur-sm">
      {links.map((l) => (
        <Link
          key={l.to}
          to={l.to}
          className={
            loc.pathname === l.to
              ? "font-semibold text-sky-400"
              : "dark:text-slate-400 light:text-slate-600 dark:hover:text-slate-200 light:hover:text-slate-900"
          }
        >
          {l.label}
        </Link>
      ))}
      <button
        type="button"
        className="ml-auto rounded-md border dark:border-slate-700 light:border-slate-300 px-2 py-1 text-xs dark:text-slate-300 light:text-slate-700"
        onClick={onToggleTheme}
      >
        {theme === "dark" ? "Light mode" : "Dark mode"}
      </button>
    </nav>
  );
}

export default function App() {
  const [theme, setTheme] = useState(() => getStoredTheme());

  return (
    <div className="min-h-screen">
      <header className="border-b dark:border-slate-800 light:border-slate-200 px-6 py-4 dark:bg-slate-950/50 light:bg-white/60">
        <div className="mx-auto flex max-w-6xl items-center gap-3">
          <img src="/logo.png" alt="RADA" className="h-8 w-8 rounded-md" />
          <div>
            <div className="text-lg font-semibold tracking-tight">RADA</div>
            <div className="text-xs dark:text-slate-500 light:text-slate-500">Risk-Aware Decision Agent</div>
          </div>
        </div>
      </header>
      <Nav theme={theme} onToggleTheme={() => setTheme(cycleTheme())} />
      <main className="mx-auto max-w-6xl px-6 py-6">
        <Routes>
          <Route path="/" element={<Overview />} />
          <Route path="/decisions" element={<Decisions />} />
          <Route path="/review" element={<ReviewQueue />} />
          <Route path="/audit" element={<Audit />} />
          <Route path="*" element={<Navigate to="/" replace />} />
        </Routes>
      </main>
    </div>
  );
}
