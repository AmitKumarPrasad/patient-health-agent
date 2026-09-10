"use client";

import { useEffect } from "react";
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

export default function AdminPage() {
  const auth = useAuth();

  useEffect(() => {
    if (auth.ready && auth.authenticated && auth.hasRole("admin")) {
      document.title = "Admin Operations";
    }
  }, [auth.ready, auth.authenticated, auth.roles]);

  if (!auth.ready) return <main className="container"><p>Loading…</p></main>;
  if (!auth.authenticated) {
    return <main className="container"><h1>Admin Operations</h1><p>Sign in to access administration.</p></main>;
  }
  if (!auth.hasRole("admin")) {
    return <main className="container"><h1>Admin Operations</h1><p>You do not have permission to access administration.</p></main>;
  }

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
          <a className="button secondary" href="http://localhost:8000/health" target="_blank" rel="noreferrer">API health</a>
          <a className="button secondary" href="http://localhost:8000/ready" target="_blank" rel="noreferrer">API readiness</a>
          <a className="button secondary" href="/admin/audit">Review recent audit events</a>
        </div>
      </section>
    </main>
  );
}
