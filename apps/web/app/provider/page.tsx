"use client";

import { FormEvent, useEffect, useMemo, useState } from "react";
import { api, Appointment, Availability, PatientDocument, Provider } from "../../lib/api";
import { useAuth } from "../providers";

function formatDateTime(value: string) {
  return new Intl.DateTimeFormat("en-IN", {
    dateStyle: "medium",
    timeStyle: "short",
    timeZone: "UTC",
  }).format(new Date(value));
}

function formatDate(value: string) {
  return new Intl.DateTimeFormat("en-IN", { dateStyle: "medium" }).format(new Date(`${value}T00:00:00`));
}

export default function ProviderDashboard() {
  const auth = useAuth();
  const [provider, setProvider] = useState<Provider | null>(null);
  const [appointments, setAppointments] = useState<Appointment[]>([]);
  const [date, setDate] = useState(() => new Date().toISOString().slice(0, 10));
  const [startTime, setStartTime] = useState("09:00");
  const [endTime, setEndTime] = useState("09:30");
  const [availability, setAvailability] = useState<Availability[]>([]);
  const [patientId, setPatientId] = useState("");
  const [documents, setDocuments] = useState<PatientDocument[]>([]);
  const [recordContent, setRecordContent] = useState<string | null>(null);
  const [selectedDocument, setSelectedDocument] = useState<string | null>(null);
  const [message, setMessage] = useState("");
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(true);

  const patientIds = useMemo(
    () => [...new Set(appointments.map((appointment) => appointment.patient_id))],
    [appointments],
  );

  useEffect(() => {
    if (!auth.ready || !auth.authenticated || !auth.hasRole("provider")) return;
    void loadDashboard();
  }, [auth.ready, auth.authenticated, auth.roles]);

  async function loadDashboard() {
    setLoading(true);
    setError("");
    try {
      const [me, items] = await Promise.all([api.providerMe(), api.appointments()]);
      setProvider(me);
      setAppointments(items);
      setPatientId((current) => current || items[0]?.patient_id || "");
    } catch (err) {
      setError(err instanceof Error ? err.message : "Unable to load provider dashboard");
    } finally {
      setLoading(false);
    }
  }

  async function loadAvailability(value = date) {
    if (!provider) return;
    setError("");
    try {
      setAvailability(await api.availability(provider.id, value));
    } catch (err) {
      setError(err instanceof Error ? err.message : "Unable to load availability");
    }
  }

  async function addAvailability(event: FormEvent) {
    event.preventDefault();
    setError("");
    setMessage("");
    try {
      await api.createProviderAvailability({ available_date: date, start_time: startTime, end_time: endTime });
      await loadAvailability();
      setMessage("Availability slot added.");
    } catch (err) {
      setError(err instanceof Error ? err.message : "Unable to add availability");
    }
  }

  async function loadPatientRecords(event: FormEvent) {
    event.preventDefault();
    if (!patientId.trim()) return;
    setError("");
    setMessage("");
    setSelectedDocument(null);
    setRecordContent(null);
    try {
      setDocuments(await api.providerRecords(patientId.trim()));
      setMessage("Authorized patient records loaded.");
    } catch (err) {
      setDocuments([]);
      setError(err instanceof Error ? err.message : "Unable to load patient records");
    }
  }

  async function openRecord(document: PatientDocument) {
    setSelectedDocument(document.id);
    setRecordContent(null);
    setError("");
    try {
      const result = await api.providerRecord(patientId, document.id);
      if (result.content !== null) setRecordContent(result.content);
      else setRecordContent("Binary document access is available through the provider API; preview is not enabled for this file type.");
    } catch (err) {
      setError(err instanceof Error ? err.message : "Unable to open record");
    }
  }

  async function updateStatus(appointment: Appointment, status: string) {
    setError("");
    try {
      await api.updateStatus(appointment.id, status);
      setAppointments(await api.appointments());
    } catch (err) {
      setError(err instanceof Error ? err.message : "Unable to update appointment");
    }
  }

  if (!auth.ready) return <main className="center"><p>Loading authentication…</p></main>;
  if (!auth.authenticated) {
    return <main className="center"><div className="card auth-card"><h1>Provider workspace</h1><p className="muted">Sign in with a provider account to continue.</p><button onClick={() => void auth.login()}>Sign in</button></div></main>;
  }
  if (!auth.hasRole("provider")) {
    return <main className="center"><div className="card auth-card"><h1>Provider access required</h1><p className="muted">This workspace is restricted to users with the provider Keycloak role.</p></div></main>;
  }

  return (
    <main>
      <header className="topbar">
        <div className="brand">Provider Health Workspace</div>
        <nav className="nav">
          <a href="#appointments">Appointments</a>
          <a href="#availability">Availability</a>
          <a href="#records">Patient records</a>
          <button className="secondary" onClick={() => void auth.logout()}>Sign out</button>
        </nav>
      </header>

      <div className="container">
        <section className="hero">
          <p className="eyebrow">Provider dashboard</p>
          <h1>{provider ? `Welcome, Dr. ${provider.first_name} ${provider.last_name}` : "Provider workspace"}</h1>
          <p className="subtitle">Manage your appointment schedule and review patient records only for patients with an active or historical appointment relationship.</p>
        </section>

        {error && <div className="error" role="alert" aria-live="assertive" style={{ marginBottom: 18 }}>{error}</div>}
        {message && <div className="success" role="status" aria-live="polite" style={{ marginBottom: 18 }}>{message}</div>}
        {loading ? <p className="muted">Loading provider data…</p> : null}

        <section className="grid">
          <div className="card wide" id="appointments">
            <h2>My appointments</h2>
            {appointments.length === 0 ? <p className="muted">No appointments found.</p> : (
              <div className="list">
                {appointments.map((appointment) => (
                  <div className="list-item" key={appointment.id}>
                    <div className="row" style={{ justifyContent: "space-between" }}>
                      <strong>{formatDateTime(appointment.starts_at)}</strong>
                      <span className="status">{appointment.status}</span>
                    </div>
                    <p className="muted">Patient ID: {appointment.patient_id}</p>
                    {appointment.reason && <p>{appointment.reason}</p>}
                    <div className="row">
                      {(appointment.status === "scheduled") && <button className="secondary" onClick={() => void updateStatus(appointment, "confirmed")}>Confirm</button>}
                      {(appointment.status === "scheduled" || appointment.status === "confirmed") && <button className="danger" onClick={() => void updateStatus(appointment, "cancelled")}>Cancel</button>}
                      {appointment.status === "confirmed" && <button onClick={() => void updateStatus(appointment, "completed")}>Mark completed</button>}
                      {appointment.status === "confirmed" && <button className="secondary" onClick={() => void loadPatientRecordsFor(appointment.patient_id)}>View patient records</button>}
                    </div>
                  </div>
                ))}
              </div>
            )}
          </div>

          <div className="card" id="availability">
            <h2>Manage availability</h2>
            <form className="chat" onSubmit={addAvailability}>
              <label>Date<input type="date" value={date} onChange={(event) => { setDate(event.target.value); void loadAvailability(event.target.value); }} /></label>
              <div className="row">
                <label>Start<input type="time" value={startTime} onChange={(event) => setStartTime(event.target.value)} /></label>
                <label>End<input type="time" value={endTime} onChange={(event) => setEndTime(event.target.value)} /></label>
              </div>
              <button type="submit">Add slot</button>
            </form>
            <div className="list" style={{ marginTop: 16 }}>
              {availability.map((slot) => <div className="list-item" key={slot.id}><strong>{formatDate(slot.available_date)}</strong><p className="muted">{slot.start_time}–{slot.end_time}</p></div>)}
              {availability.length === 0 ? <p className="muted">No slots loaded for this date.</p> : null}
            </div>
          </div>

          <div className="card full" id="records">
            <h2>Authorized patient records</h2>
            <p className="muted">Access is enforced server-side using the provider-to-patient appointment relationship. IDs below are taken from your appointment list.</p>
            <form className="row" onSubmit={loadPatientRecords}>
              <select value={patientId} onChange={(event) => setPatientId(event.target.value)} aria-label="Patient">
                <option value="">Select patient</option>
                {patientIds.map((id) => <option key={id} value={id}>{id}</option>)}
              </select>
              <button type="submit">Load records</button>
            </form>
            {documents.length === 0 ? <p className="muted" style={{ marginTop: 14 }}>No records loaded.</p> : (
              <div className="list" style={{ marginTop: 14 }}>
                {documents.map((document) => (
                  <div className="list-item" key={document.id}>
                    <div className="row" style={{ justifyContent: "space-between" }}>
                      <div><strong>{document.original_filename}</strong>{document.category ? <span className="status" style={{ marginLeft: 8 }}>{document.category}</span> : null}</div>
                      <button className="secondary" disabled={selectedDocument === document.id} onClick={() => void openRecord(document)}>{selectedDocument === document.id ? "Opening…" : "Open"}</button>
                    </div>
                    <p className="muted">{document.content_type} · {document.description || "No description"}</p>
                  </div>
                ))}
              </div>
            )}
            {recordContent !== null ? <pre className="chat-answer" style={{ marginTop: 14, whiteSpace: "pre-wrap", overflowX: "auto" }}>{recordContent}</pre> : null}
          </div>
        </section>
      </div>
    </main>
  );

  async function loadPatientRecordsFor(id: string) {
    setPatientId(id);
    setError("");
    try {
      setDocuments(await api.providerRecords(id));
      setMessage("Authorized patient records loaded.");
      document.getElementById("records")?.scrollIntoView({ behavior: "smooth" });
    } catch (err) {
      setDocuments([]);
      setError(err instanceof Error ? err.message : "Unable to load patient records");
    }
  }
}
