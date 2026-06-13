import { useMemo, useState } from "react";
import { Link, Navigate, Route, Routes, useLocation } from "react-router-dom";
import { Audit } from "./pages/Audit";
import { Decisions } from "./pages/Decisions";
import { Overview } from "./pages/Overview";
import { ReviewQueue } from "./pages/ReviewQueue";
import { cycleTheme, getStoredTheme } from "./theme";

const links = [
  { to: "/", label: "Mission Control", short: "Control" },
  { to: "/decisions", label: "Decision Studio", short: "Decisions" },
  { to: "/review", label: "Review Desk", short: "Review" },
  { to: "/audit", label: "Audit Vault", short: "Audit" },
];

function StatusDot({ online }) {
  return (
    <span
      className={`status-dot ${online ? "status-dot--online" : "status-dot--offline"}`}
      aria-label={online ? "API online" : "API offline"}
    />
  );
}

function Navigation() {
  const loc = useLocation();

  return (
    <nav className="app-nav" aria-label="Primary navigation">
      {links.map((link) => {
        const active = loc.pathname === link.to;
        return (
          <Link key={link.to} to={link.to} className={active ? "app-nav__item is-active" : "app-nav__item"}>
            <span className="app-nav__long">{link.label}</span>
            <span className="app-nav__short">{link.short}</span>
          </Link>
        );
      })}
    </nav>
  );
}

export default function App() {
  const [theme, setTheme] = useState(() => getStoredTheme());
  const [onlineHint, setOnlineHint] = useState(true);

  const modeLabel = useMemo(
    () => (theme === "dark" ? "Switch to day mode" : "Switch to night mode"),
    [theme],
  );

  return (
    <div className="app-root">
      <div className="bg-orbit bg-orbit--one" />
      <div className="bg-orbit bg-orbit--two" />

      <header className="app-header">
        <div className="app-header__brand">
          <img src="/logo.png" alt="RADA" className="app-logo" />
          <div>
            <p className="app-kicker">Risk-Aware Decision Agent</p>
            <h1>Operator Console</h1>
          </div>
        </div>

        <div className="app-header__actions">
          <button
            type="button"
            className="action-btn action-btn--ghost"
            onClick={() => setTheme(cycleTheme())}
          >
            {modeLabel}
          </button>
          <button
            type="button"
            className="action-btn"
            onClick={() => setOnlineHint((prev) => !prev)}
            title="Toggle API hint"
          >
            <StatusDot online={onlineHint} />
            API hint
          </button>
        </div>
      </header>

      <Navigation />

      <section className="app-intro-card">
        <div>
          <h2>Runbook Friendly by Design</h2>
          <p>
            This dashboard is the complete operator surface for runtime health, manual decision
            simulation, review actions, and audit export. Use Streamlit for lightweight smoke tests.
          </p>
        </div>
        <ul>
          <li>Mission Control for live API and KPI checks</li>
          <li>Decision Studio for ingest and deep decision inspection</li>
          <li>Review Desk for triage and feedback actions</li>
          <li>Audit Vault for event retrieval and NDJSON export</li>
        </ul>
      </section>

      <main className="app-main">
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
