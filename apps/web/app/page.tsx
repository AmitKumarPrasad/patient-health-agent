"use client";

import { FormEvent, useEffect, useState } from "react";
import { api, Appointment, Availability, Patient, PatientDocument, Provider } from "../lib/api";
import { useAuth } from "./providers";

function formatDate(value: string) {
  return new Intl.DateTimeFormat("en-IN", {
    dateStyle: "medium",
    timeStyle: "short",
  }).format(new Date(value));
}

function formatBytes(value: number) {
  if (value < 1024) return `${value} B`;
  if (value < 1024 * 1024) return `${Math.round(value / 1024)} KB`;
  return `${(value / (1024 * 1024)).toFixed(1)} MB`;
}

export default function Home() {
  const auth = useAuth();
  const [patient, setPatient] = useState<Patient | null>(null);
  const [appointments, setAppointments] = useState<Appointment[]>([]);
  const [providers, setProviders] = useState<Provider[]>([]);
  const [availability, setAvailability] = useState<Availability[]>([]);
  const [documents, setDocuments] = useState<PatientDocument[]>([]);
  const [specialty, setSpecialty] = useState("");
  const [selectedProvider, setSelectedProvider] = useState<Provider | null>(null);
  const [date, setDate] = useState(() => new Date().toISOString().slice(0, 10));
  const [reason, setReason] = useState("");
  const [message, setMessage] = useState("");
  const [answer, setAnswer] = useState("");
  const [recordMessage, setRecordMessage] = useState("");
  const [recordAnswer, setRecordAnswer] = useState("");
  const [recordQuery, setRecordQuery] = useState("");
  const [uploadCategory, setUploadCategory] = useState("");
  const [uploadDescription, setUploadDescription] = useState("");
  const [selectedFile, setSelectedFile] = useState<File | null>(null);
  const [loading, setLoading] = useState(false);
  const [recordLoading, setRecordLoading] = useState(false);
  const [uploading, setUploading] = useState(false);
  const [error, setError] = useState("");
  const [recordError, setRecordError] = useState("");

  useEffect(() => {
    if (!auth.ready || !auth.authenticated) return;
    void loadDashboard();
  }, [auth.ready, auth.authenticated]);

  async function loadDashboard() {
    setLoading(true);
    setError("");
    try {
      const [me, upcoming, providerList, patientDocuments] = await Promise.all([
        api.me(),
        api.appointments(),
        api.providers(),
        api.documents(),
      ]);
      setPatient(me);
      setAppointments(upcoming);
      setProviders(providerList);
      setDocuments(patientDocuments);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Unable to load dashboard");
    } finally {
      setLoading(false);
    }
  }

  async function searchProviders(event: FormEvent) {
    event.preventDefault();
    setError("");
    try {
      setProviders(await api.providers(specialty));
    } catch (err) {
      setError(err instanceof Error ? err.message : "Unable to search providers");
    }
  }

  async function selectProvider(provider: Provider) {
    setSelectedProvider(provider);
    setError("");
    try {
      setAvailability(await api.availability(provider.id, date));
    } catch (err) {
      setError(err instanceof Error ? err.message : "Unable to load availability");
    }
  }

  async function changeDate(value: string) {
    setDate(value);
    if (!selectedProvider) return;
    try {
      setAvailability(await api.availability(selectedProvider.id, value));
    } catch (err) {
      setError(err instanceof Error ? err.message : "Unable to load availability");
    }
  }

  async function book(slot: Availability) {
    if (!selectedProvider) return;
    setError("");
    try {
      await api.book({
        provider_id: selectedProvider.id,
        starts_at: slot.start_time,
        ends_at: slot.end_time,
        reason: reason || undefined,
      });
      setReason("");
      setAvailability((items) => items.filter((item) => item.id !== slot.id));
      setAppointments(await api.appointments());
    } catch (err) {
      setError(err instanceof Error ? err.message : "Unable to book appointment");
    }
  }

  async function cancel(appointment: Appointment) {
    setError("");
    try {
      await api.updateStatus(appointment.id, "cancelled");
      setAppointments(await api.appointments());
    } catch (err) {
      setError(err instanceof Error ? err.message : "Unable to cancel appointment");
    }
  }

  async function askAssistant(event: FormEvent) {
    event.preventDefault();
    if (!message.trim()) return;
    setLoading(true);
    setError("");
    try {
      const result = await api.chat(message.trim());
      setAnswer(result.response);
      setMessage("");
    } catch (err) {
      setError(err instanceof Error ? err.message : "Assistant request failed");
    } finally {
      setLoading(false);
    }
  }

  async function askRecordAssistant(event: FormEvent) {
    event.preventDefault();
    if (!recordMessage.trim()) return;
    setRecordLoading(true);
    setRecordError("");
    try {
      const result = await api.recordAssistant(recordMessage.trim());
      setRecordAnswer(result.response);
      setRecordMessage("");
    } catch (err) {
      setRecordError(err instanceof Error ? err.message : "Record assistant request failed");
    } finally {
      setRecordLoading(false);
    }
  }

  async function searchRecords(event: FormEvent) {
    event.preventDefault();
    setRecordError("");
    try {
      const result = await api.searchRecords(recordQuery.trim());
      setDocuments(result.documents);
    } catch (err) {
      setRecordError(err instanceof Error ? err.message : "Unable to search records");
    }
  }

  async function uploadRecord(event: FormEvent) {
    event.preventDefault();
    if (!selectedFile) return;
    setUploading(true);
    setRecordError("");
    try {
      const document = await api.uploadDocument(selectedFile, uploadCategory, uploadDescription);
      setDocuments((items) => [document, ...items]);
      setSelectedFile(null);
      setUploadCategory("");
      setUploadDescription("");
      const fileInput = document.getElementById("record-file") as HTMLInputElement | null;
      if (fileInput) fileInput.value = "";
    } catch (err) {
      setRecordError(err instanceof Error ? err.message : "Unable to upload record");
    } finally {
      setUploading(false);
    }
  }

  if (!auth.ready) {
    return <main className="container"><p className="muted">Loading secure session…</p></main>;
  }

  if (!auth.authenticated) {
    return (
      <main className="container">
        <section className="hero">
          <p className="eyebrow">Patient Health Agent</p>
          <h1>Secure healthcare appointment management</h1>
          <p className="subtitle">Sign in with Keycloak to search providers, book appointments and use the AI workflow assistant.</p>
        </section>
        <section className="card" style={{ maxWidth: 520 }}>
          <h2>Sign in</h2>
          <p className="muted">Authentication is handled by your configured Keycloak realm.</p>
          <button onClick={() => void auth.login()}>Continue to login</button>
        </section>
      </main>
    );
  }

  return (
    <main className="page">
      <header className="topbar">
        <div className="brand">Patient Health Agent</div>
        <nav className="nav">
          <a href="#appointments">Appointments</a>
          <a href="#records">Records</a>
          <a href="#providers">Providers</a>
          <a href="#assistant">AI Assistant</a>
          <button className="secondary" onClick={() => void auth.logout()}>Sign out</button>
        </nav>
      </header>

      <div className="container">
        <section className="hero">
          <p className="eyebrow">Patient dashboard</p>
          <h1>Welcome{patient ? `, ${patient.first_name}` : ""}</h1>
          <p className="subtitle">Manage appointments and use your record assistant to find information in your own uploaded health documents. The AI does not provide clinical diagnosis or treatment decisions.</p>
        </section>

        {error && <div className="error" style={{ marginBottom: 18 }}>{error}</div>}

        <section className="grid">
          <div className="card wide" id="appointments">
            <h2>My appointments</h2>
            {loading && appointments.length === 0 ? <p className="muted">Loading…</p> : null}
            {appointments.length === 0 ? (
              <p className="muted">No appointments yet.</p>
            ) : (
              <div className="list">
                {appointments.map((appointment) => (
                  <div className="list-item" key={appointment.id}>
                    <div className="row" style={{ justifyContent: "space-between" }}>
                      <strong>{formatDate(appointment.starts_at)}</strong>
                      <span className="status">{appointment.status}</span>
                    </div>
                    <p className="muted">Appointment type: {appointment.appointment_type}</p>
                    {appointment.reason && <p>{appointment.reason}</p>}
                    {(appointment.status === "scheduled" || appointment.status === "confirmed") && (
                      <button className="danger" onClick={() => void cancel(appointment)}>Cancel appointment</button>
                    )}
                  </div>
                ))}
              </div>
            )}
          </div>

          <div className="card" id="assistant">
            <h2>AI appointment assistant</h2>
            <form className="chat" onSubmit={askAssistant}>
              <textarea value={message} onChange={(event) => setMessage(event.target.value)} placeholder="e.g. Find me a cardiologist and help me book an appointment." />
              <button disabled={loading}>{loading ? "Working…" : "Ask assistant"}</button>
            </form>
            {answer && <div className="chat-answer" style={{ marginTop: 12 }}>{answer}</div>}
          </div>

          <div className="card full" id="records">
            <div className="row" style={{ justifyContent: "space-between", marginBottom: 12 }}>
              <div>
                <h2 style={{ marginBottom: 4 }}>My health records</h2>
                <p className="muted">Upload your own records and ask the record assistant to find relevant information.</p>
              </div>
            </div>
            {recordError && <div className="error" style={{ marginBottom: 14 }}>{recordError}</div>}
            <div className="records-grid">
              <div className="record-panel">
                <h3>Upload a record</h3>
                <form className="chat" onSubmit={uploadRecord}>
                  <input id="record-file" type="file" accept="application/pdf,image/jpeg,image/png,text/plain" onChange={(event) => setSelectedFile(event.target.files?.[0] ?? null)} />
                  <input value={uploadCategory} onChange={(event) => setUploadCategory(event.target.value)} placeholder="Category, e.g. lab report" />
                  <input value={uploadDescription} onChange={(event) => setUploadDescription(event.target.value)} placeholder="Short description (optional)" />
                  <button disabled={!selectedFile || uploading}>{uploading ? "Uploading…" : "Upload record"}</button>
                </form>
              </div>

              <div className="record-panel">
                <h3>Record assistant</h3>
                <form className="chat" onSubmit={askRecordAssistant}>
                  <textarea value={recordMessage} onChange={(event) => setRecordMessage(event.target.value)} placeholder="e.g. Find my latest lab report." />
                  <button disabled={recordLoading}>{recordLoading ? "Searching…" : "Ask about my records"}</button>
                </form>
                {recordAnswer && <div className="chat-answer" style={{ marginTop: 12 }}>{recordAnswer}</div>}
              </div>
            </div>

            <div className="record-list-header">
              <div>
                <h3>Document library</h3>
                <p className="muted">Only records belonging to your authenticated patient account are returned.</p>
              </div>
              <form className="row" onSubmit={searchRecords}>
                <input value={recordQuery} onChange={(event) => setRecordQuery(event.target.value)} placeholder="Search filename, category or description" />
                <button className="secondary" type="submit">Search</button>
              </form>
            </div>

            {documents.length === 0 ? (
              <p className="muted">No uploaded records found.</p>
            ) : (
              <div className="list">
                {documents.map((document) => (
                  <div className="list-item" key={document.id}>
                    <div className="row" style={{ justifyContent: "space-between" }}>
                      <strong>{document.original_filename}</strong>
                      <span className="status">{document.category || "uncategorized"}</span>
                    </div>
                    <p className="muted">{document.content_type} · {formatBytes(document.size_bytes)} · uploaded {formatDate(document.created_at)}</p>
                    {document.description && <p>{document.description}</p>}
                  </div>
                ))}
              </div>
            )}
          </div>

          <div className="card full" id="providers">
            <h2>Find a provider</h2>
            <form className="row" onSubmit={searchProviders}>
              <div style={{ flex: "1 1 260px" }}>
                <input value={specialty} onChange={(event) => setSpecialty(event.target.value)} placeholder="Specialty, e.g. cardiology" />
              </div>
              <button type="submit">Search</button>
            </form>
            <div className="list" style={{ marginTop: 14 }}>
              {providers.map((provider) => (
                <div className="list-item" key={provider.id}>
                  <div className="row" style={{ justifyContent: "space-between" }}>
                    <div>
                      <strong>{provider.first_name} {provider.last_name}</strong>
                      <div className="muted">{provider.specialty}</div>
                    </div>
                    <button className="secondary" onClick={() => void selectProvider(provider)}>View availability</button>
                  </div>
                  {provider.bio && <p className="muted" style={{ marginTop: 8 }}>{provider.bio}</p>}
                </div>
              ))}
            </div>
          </div>

          {selectedProvider && (
            <div className="card full">
              <div className="row" style={{ justifyContent: "space-between" }}>
                <div>
                  <h2 style={{ marginBottom: 4 }}>Availability: {selectedProvider.first_name} {selectedProvider.last_name}</h2>
                  <p className="muted">{selectedProvider.specialty}</p>
                </div>
                <input style={{ width: 170 }} type="date" value={date} onChange={(event) => void changeDate(event.target.value)} />
              </div>
              <input value={reason} onChange={(event) => setReason(event.target.value)} placeholder="Reason for visit (optional)" style={{ marginBottom: 14 }} />
              {availability.length === 0 ? (
                <p className="muted">No open slots for this date.</p>
              ) : (
                <div className="row">
                  {availability.map((slot) => (
                    <button key={slot.id} onClick={() => void book(slot)}>
                      {new Date(slot.start_time).toLocaleTimeString("en-IN", { hour: "2-digit", minute: "2-digit" })}
                      {" – "}
                      {new Date(slot.end_time).toLocaleTimeString("en-IN", { hour: "2-digit", minute: "2-digit" })}
                    </button>
                  ))}
                </div>
              )}
            </div>
          )}
        </section>
      </div>
    </main>
  );
}
