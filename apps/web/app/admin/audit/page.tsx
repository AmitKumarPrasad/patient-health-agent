"use client";

import { FormEvent, useEffect, useState } from "react";
import { API_URL } from "../../../lib/api";
import { getKeycloak } from "../../keycloak";
import { useAuth } from "../../providers";

type AuditEvent = {
  id: string;
  actor_subject: string;
  actor_role: string;
  action: string;
  resource_type: string;
  resource_id: string | null;
  patient_id: string | null;
  created_at: string;
  outcome: string;
  metadata: Record<string, unknown> | null;
};

const PAGE_SIZE = 100;

export default function AdminAuditPage() {
  const auth = useAuth();
  const [events, setEvents] = useState<AuditEvent[]>([]);
  const [action, setAction] = useState("");
  const [actor, setActor] = useState("");
  const [patientId, setPatientId] = useState("");
  const [outcome, setOutcome] = useState("");
  const [offset, setOffset] = useState(0);
  const [loading, setLoading] = useState(false);
  const [processing, setProcessing] = useState(false);
  const [exporting, setExporting] = useState(false);
  const [processMessage, setProcessMessage] = useState("");
  const [error, setError] = useState("");

  function buildFilterParams(): URLSearchParams {
    const params = new URLSearchParams();
    if (action.trim()) params.set("action", action.trim());
    if (actor.trim()) params.set("actor_subject", actor.trim());
    if (patientId.trim()) params.set("patient_id", patientId.trim());
    if (outcome.trim()) params.set("outcome", outcome.trim());
    return params;
  }

  async function loadEvents(event?: FormEvent, nextOffset = offset) {
    event?.preventDefault();
    if (!auth.authenticated || !auth.hasRole("admin")) return;
    setLoading(true);
    setError("");
    try {
      const keycloak = getKeycloak();
      await keycloak.updateToken(30);
      const params = buildFilterParams();
      params.set("limit", String(PAGE_SIZE));
      params.set("offset", String(nextOffset));
      const response = await fetch(`${API_URL}/api/admin/audit?${params.toString()}`, {
        headers: { Authorization: `Bearer ${keycloak.token ?? ""}` },
      });
      if (!response.ok) {
        const body = await response.json().catch(() => null);
        throw new Error(body?.detail ?? `Request failed with status ${response.status}`);
      }
      setEvents((await response.json()) as AuditEvent[]);
      setOffset(nextOffset);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Unable to load audit events");
    } finally {
      setLoading(false);
    }
  }

  async function processNotifications() {
    if (!auth.authenticated || !auth.hasRole("admin")) return;
    setProcessing(true);
    setError("");
    setProcessMessage("");
    try {
      const keycloak = getKeycloak();
      await keycloak.updateToken(30);
      const response = await fetch(`${API_URL}/api/admin/notifications/process`, {
        method: "POST",
        headers: { Authorization: `Bearer ${keycloak.token ?? ""}` },
      });
      const body = await response.json().catch(() => null);
      if (!response.ok) {
        throw new Error(body?.detail ?? `Request failed with status ${response.status}`);
      }
      setProcessMessage(`${body?.processed ?? 0} due notification(s) processed.`);
      await loadEvents(undefined, offset);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Unable to process notifications");
    } finally {
      setProcessing(false);
    }
  }

  async function exportCsv() {
    if (!auth.authenticated || !auth.hasRole("admin")) return;
    setExporting(true);
    setError("");
    try {
      const keycloak = getKeycloak();
      await keycloak.updateToken(30);
      const params = buildFilterParams();
      const response = await fetch(`${API_URL}/api/admin/audit/export?${params.toString()}`, {
        headers: { Authorization: `Bearer ${keycloak.token ?? ""}` },
      });
      if (!response.ok) {
        const body = await response.json().catch(() => null);
        throw new Error(body?.detail ?? `Request failed with status ${response.status}`);
      }
      const blob = await response.blob();
      const url = URL.createObjectURL(blob);
      const link = document.createElement("a");
      link.href = url;
      link.download = "audit-events.csv";
      document.body.appendChild(link);
      link.click();
      link.remove();
      URL.revokeObjectURL(url);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Unable to export audit events");
    } finally {
      setExporting(false);
    }
  }

  function applyFilters(event: FormEvent) {
    void loadEvents(event, 0);
  }

  function changePage(nextOffset: number) {
    if (nextOffset < 0 || loading) return;
    void loadEvents(undefined, nextOffset);
  }

  useEffect(() => {
    if (auth.ready && auth.authenticated && auth.hasRole("admin")) void loadEvents(undefined, 0);
  }, [auth.ready, auth.authenticated, auth.roles]);

  if (!auth.ready) return <main className="container"><p>Loading…</p></main>;
  if (!auth.authenticated) {
    return <main className="container"><h1>Admin Audit</h1><p>Sign in to access the audit log.</p></main>;
  }
  if (!auth.hasRole("admin")) {
    return <main className="container"><h1>Admin Audit</h1><p>You do not have permission to view audit events.</p></main>;
  }

  return (
    <main className="container">
      <div className="page-header">
        <div>
          <p className="eyebrow">Administration</p>
          <h1>Audit log</h1>
          <p className="muted">Review security-relevant activity across patients, providers, appointments, and records.</p>
        </div>
        <div className="row">
          <button className="button secondary" disabled={processing} onClick={() => void processNotifications()}>
            {processing ? "Processing…" : "Process due notifications"}
          </button>
          <a href="/" className="button secondary">Dashboard</a>
        </div>
      </div>

      {processMessage && <p className="success">{processMessage}</p>}

      <form className="card filter-grid" onSubmit={applyFilters}>
        <label>Action<input value={action} onChange={(e) => setAction(e.target.value)} placeholder="appointment.booked" /></label>
        <label>Actor subject<input value={actor} onChange={(e) => setActor(e.target.value)} placeholder="user or subject" /></label>
        <label>Patient ID<input value={patientId} onChange={(e) => setPatientId(e.target.value)} placeholder="UUID" /></label>
        <label>Outcome<select value={outcome} onChange={(e) => setOutcome(e.target.value)}><option value="">Any</option><option value="success">Success</option><option value="failure">Failure</option></select></label>
        <button className="button" disabled={loading}>{loading ? "Loading…" : "Apply filters"}</button>
      </form>

      {error && <p className="error">{error}</p>}

      <section className="card table-wrap" aria-label="Audit events">
        <div className="table-title">
          <div className="row">
            <strong>{events.length} events</strong>
            <span className="muted">Page {Math.floor(offset / PAGE_SIZE) + 1}</span>
          </div>
          <button className="button secondary" disabled={loading || exporting} onClick={() => void exportCsv()}>
            {exporting ? "Exporting…" : "Export filtered CSV"}
          </button>
        </div>
        <table>
          <thead><tr><th>Time</th><th>Action</th><th>Actor</th><th>Resource</th><th>Patient</th><th>Outcome</th><th>Metadata</th></tr></thead>
          <tbody>
            {events.map((event) => (
              <tr key={event.id}>
                <td>{new Date(event.created_at).toLocaleString("en-IN")}</td>
                <td><strong>{event.action}</strong><div className="muted">{event.actor_role}</div></td>
                <td>{event.actor_subject}</td>
                <td>{event.resource_type}{event.resource_id ? <div className="muted">{event.resource_id}</div> : null}</td>
                <td>{event.patient_id ?? "—"}</td>
                <td><span className={`status ${event.outcome === "success" ? "success" : "failure"}`}>{event.outcome}</span></td>
                <td><code>{event.metadata ? JSON.stringify(event.metadata) : "—"}</code></td>
              </tr>
            ))}
            {!loading && events.length === 0 && <tr><td colSpan={7} className="empty">No audit events match the current filters.</td></tr>}
          </tbody>
        </table>
        <div className="row" style={{ justifyContent: "space-between", marginTop: "1rem" }}>
          <button className="button secondary" disabled={loading || offset === 0} onClick={() => changePage(offset - PAGE_SIZE)}>
            Previous
          </button>
          <span className="muted">Showing {events.length} of up to {PAGE_SIZE} events</span>
          <button className="button secondary" disabled={loading || events.length < PAGE_SIZE} onClick={() => changePage(offset + PAGE_SIZE)}>
            Next
          </button>
        </div>
      </section>
    </main>
  );
}
