"use client";

import { useEffect, useState } from "react";
import { API_URL } from "../../lib/api";
import { useAuth } from "../providers";

const cards = [
  {
    title: "Audit log",
    description: "Review security-relevant activity across patients, providers, appointments, and records.",
    href: "/admin/audit",
    action: "Open audit log",
  },
  {
    title: "Notification operations",
    description: "Process due appointment notifications and verify the resulting audit event.",
    href: "/admin/audit",
    action: "Process notifications",
  },
];

type CheckState = "checking" | "healthy" | "unhealthy";

export default function AdminPage() {
  const auth = useAuth();
  const [health, setHealth] = useState<CheckState>("checking");
  const [readiness, setReadiness] = useState<CheckState>("checking");

  useEffect(() => {
    if (auth.ready && auth.authenticated && auth.hasRole("admin")) {
      document.title = "Admin Operations";
    }
  }, [auth.ready, auth.authenticated, auth.roles]);

  useEffect(() => {
    if (!auth.ready || !auth.authenticated || !auth.hasRole("admin")) return;

    let active = true;
    const check = async (path: string, setState: (state: CheckState) => void) => {
      try {
        const response = await fetch(`${API_URL}${path}`, { cache: "no-store" });
        if (active) setState(response.ok ? "healthy" : "unhealthy");
      } catch {
        if (active) setState("unhealthy");
      }
    };

    void Promise.all([
      check("/health", setHealth),
      check("/ready", setReadiness),
    ]);

    return () => {
      active = false;
    };
  }, [auth.ready, auth.authenticated, auth.roles]);

  if (!auth.ready) return <main className="container"><p>Loading…</p></main>;
  if (!auth.authenticated) {
    return <main className="container"><h1>Admin Operations</h1><p>Sign in to access administration.</p></main>;
  }
  if (!auth.hasRole("admin")) {
    return <main className="container"><h1>Admin Operations</h1><p>You do not have permission to access administration.</p></main>;
  }

  const statusLabel = (state: CheckState) =>
    state === "checking" ? "Checking…" : state === "healthy" ? "Healthy" : "Unavailable";

  return (
    <main className="container">
      <div className="page-header">
        <div>
          <p className="eyebrow">Administration</p>
          <h1>Operations center</h1>
          <p className="muted">Manage audit review and operational notification processing from one place.</p>
        </div>
        <a href="/" className="button secondary">Dashboard</a>
      </div>

      <div className="card-grid">
        {cards.map((card) => (
          <section className="card" key={card.title}>
            <h2>{card.title}</h2>
            <p className="muted">{card.description}</p>
            <a className="button" href={card.href}>{card.action}</a>
          </section>
        ))}
      </div>

      <section className="card" style={{ marginTop: "1rem" }}>
        <h2>Operational checks</h2>
        <div className="row">
          <span className="button secondary" aria-live="polite">API health: {statusLabel(health)}</span>
          <span className="button secondary" aria-live="polite">API readiness: {statusLabel(readiness)}</span>
          <a className="button secondary" href={`${API_URL}/health`} target="_blank" rel="noreferrer">Open health endpoint</a>
          <a className="button secondary" href={`${API_URL}/ready`} target="_blank" rel="noreferrer">Open readiness endpoint</a>
        </div>
      </section>
    </main>
  );
}
