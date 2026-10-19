"use client";

import { FormEvent, useEffect, useRef, useState } from "react";
import { api, Appointment, Availability, Patient, PatientDocument, Provider } from "../lib/api";
import { useAuth } from "./providers";

const MAX_DOCUMENT_BYTES = 10 * 1024 * 1024;

function formatDate(value: string) {
  return new Intl.DateTimeFormat("en-IN", {
    dateStyle: "medium",
    timeStyle: "short",
    timeZone: "UTC",
  }).format(new Date(value));
}

function formatTime(value: string) {
  const [hours, minutes] = value.split(":").map(Number);
  if (!Number.isFinite(hours) || !Number.isFinite(minutes)) return value;
  return new Intl.DateTimeFormat("en-IN", {
    hour: "2-digit",
    minute: "2-digit",
  }).format(new Date(1970, 0, 1, hours, minutes));
}

function slotTimestamp(date: string, time: string) {
  return `${date}T${time}Z`;
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
  const [documentAction, setDocumentAction] = useState<string | null>(null);
  const [consultationAction, setConsultationAction] = useState<string | null>(null);
  const [cancellationPending, setCancellationPending] = useState<Appointment | null>(null);
  const [cancelling, setCancelling] = useState<string | null>(null);
  const cancellationDialogRef = useRef<HTMLDialogElement>(null);
  const [error, setError] = useState("");
  const [recordError, setRecordError] = useState("");

  useEffect(() => {
    if (!auth.ready || !auth.authenticated) return;
    void loadDashboard();
  }, [auth.ready, auth.authenticated]);

  useEffect(() => {
    const dialog = cancellationDialogRef.current;
    if (!dialog) return;
    if (cancellationPending && !dialog.open) dialog.showModal();
    if (!cancellationPending && dialog.open) dialog.close();
  }, [cancellationPending]);

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
        starts_at: slotTimestamp(slot.available_date, slot.start_time),
        ends_at: slotTimestamp(slot.available_date, slot.end_time),
        reason: reason || undefined,
      });
      setReason("");
      setAvailability((items) => items.filter((item) => item.id !== slot.id));
      setAppointments(await api.appointments());
    } catch (err) {
      setError(err instanceof Error ? err.message : "Unable to book appointment");
    }
  }

  function cancel(appointment: Appointment) {
    setError("");
    setCancellationPending(appointment);
  }

  async function confirmCancellation() {
    if (!cancellationPending) return;
    const appointment = cancellationPending;
    setCancelling(appointment.id);
    setError("");
    try {
      await api.updateStatus(appointment.id, "cancelled");
      setAppointments(await api.appointments());
      setCancellationPending(null);
    } catch (err) {
      setCancellationPending(null);
      setError(err instanceof Error ? err.message : "Unable to cancel appointment");
    } finally {
      setCancelling(null);
    }
  }

  async function joinConsultation(appointment: Appointment) {
    setConsultationAction(appointment.id);
    setError("");
    try {
      const result = await api.consultation(appointment.id);
      window.location.assign(result.join_url);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Unable to open video consultation");
    } finally {
      setConsultationAction(null);
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
    if (selectedFile.size > MAX_DOCUMENT_BYTES) {
      setSelectedFile(null);
      setRecordError("This file is larger than the 10 MB upload limit. Choose a smaller file.");
      return;
    }
    setUploading(true);
    setRecordError("");
    try {
      await api.uploadDocument(selectedFile, uploadCategory, uploadDescription);
      setSelectedFile(null);
      setUploadCategory("");
      setUploadDescription("");
      setDocuments(await api.documents());
    } catch (err) {
      setRecordError(err instanceof Error ? err.message : "Unable to upload record");
    } finally {
      setUploading(false);
    }
  }

  async function downloadRecord(doc: PatientDocument) {
    setDocumentAction(doc.id);
    setRecordError("");
    try {
      const blob = await api.downloadDocument(doc.id);
      const url = URL.createObjectURL(blob);
      const anchor = document.createElement("a");
      anchor.href = url;
      anchor.download = doc.original_filename;
      anchor.click();
      URL.revokeObjectURL(url);
    } catch (err) {
      setRecordError(err instanceof Error ? err.message : "Unable to download record");
    } finally {
      setDocumentAction(null);
    }
  }

  async function deleteRecord(doc: PatientDocument) {
    setDocumentAction(doc.id);
    setRecordError("");
    try {
      await api.deleteDocument(doc.id);
      setDocuments((items) => items.filter((item) => item.id !== doc.id));
    } catch (err) {
      setRecordError(err instanceof Error ? err.message : "Unable to delete record");
    } finally {
      setDocumentAction(null);
    }
  }

  if (!auth.ready) {
    return <main className="center"><p>Loading authentication…</p></main>;
  }

  if (!auth.authenticated) {
    return (
      <main className="center">
        <div className="card auth-card">
          <p className="eyebrow">Patient Health Agent</p>
          <h1>Secure healthcare workflow demo</h1>
          <p className="muted">Sign in to manage appointments, your uploaded records, and the AI assistants.</p>
          <button onClick={() => void auth.login()}>Sign in</button>
        </div>
      </main>
    );
  }

  return (
    <main>
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

        {error && <div className="error" role="alert" style={{ marginBottom: 18 }}>{error}{!loading && !patient && <button type="button" onClick={() => void loadDashboard()} style={{ marginLeft: 12 }}>Retry dashboard</button>}</div>}

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
                      <div className="row">
                        <button className="secondary" disabled={consultationAction === appointment.id} onClick={() => void joinConsultation(appointment)}>
                          {consultationAction === appointment.id ? "Opening…" : "Join video consultation"}
                        </button>
                        <button className="danger" onClick={() => void cancel(appointment)}>Cancel appointment</button>
                      </div>
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
            {recordError && <div className="error" role="alert" style={{ marginBottom: 14 }}>{recordError}</div>}
            <div className="records-grid">
              <div className="record-panel">
                <h3>Upload a record</h3>
                <form className="chat" onSubmit={uploadRecord}>
                  <label htmlFor="record-file">Choose a record</label>
                  <input
                    id="record-file"
                    type="file"
                    accept="application/pdf,image/jpeg,image/png,text/plain"
                    aria-describedby="record-file-help"
                    onChange={(event) => {
                      const file = event.currentTarget.files?.[0] ?? null;
                      setRecordError("");
                      if (file && file.size > MAX_DOCUMENT_BYTES) {
                        event.currentTarget.value = "";
                        setSelectedFile(null);
                        setRecordError("This file is larger than the 10 MB upload limit. Choose a smaller file.");
                        return;
                      }
                      setSelectedFile(file);
                    }}
                  />
                  <p id="record-file-help" className="muted">PDF, JPG, PNG, or text files up to 10 MB.</p>
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
                {documents.map((doc) => (
                  <div className="list-item" key={doc.id}>
                    <div className="row" style={{ justifyContent: "space-between", gap: 12 }}>
                      <div>
                        <strong>{doc.original_filename}</strong>
                        <span className="status" style={{ marginLeft: 8 }}>{doc.category || "uncategorized"}</span>
                      </div>
                      <div className="row">
                        <button className="secondary" disabled={documentAction === doc.id} onClick={() => void downloadRecord(doc)}>
                          {documentAction === doc.id ? "Working…" : "Download"}
                        </button>
                        <button className="danger" disabled={documentAction === doc.id} onClick={() => void deleteRecord(doc)}>
                          Delete
                        </button>
                      </div>
                    </div>
                    <p className="muted">{doc.content_type} · {formatBytes(doc.size_bytes)} · uploaded {formatDate(doc.created_at)}</p>
                    {doc.description && <p>{doc.description}</p>}
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
                      {formatTime(slot.start_time)}
                    </button>
                  ))}
                </div>
              )}
            </div>
          )}
        </section>
      </div>

      <dialog
        ref={cancellationDialogRef}
        className="confirm-dialog"
        aria-labelledby="cancel-appointment-title"
        aria-describedby="cancel-appointment-description"
        onCancel={(event) => {
          event.preventDefault();
          setCancellationPending(null);
        }}
      >
        <h2 id="cancel-appointment-title">Cancel appointment?</h2>
        <p id="cancel-appointment-description">
          {cancellationPending
            ? `Are you sure you want to cancel the appointment scheduled for ${formatDate(cancellationPending.starts_at)}?`
            : ""}
        </p>
        <div className="row" style={{ justifyContent: "flex-end" }}>
          <button
            type="button"
            className="secondary"
            autoFocus
            disabled={cancelling === cancellationPending?.id}
            onClick={() => setCancellationPending(null)}
          >
            Keep appointment
          </button>
          <button
            type="button"
            className="danger"
            disabled={!cancellationPending || cancelling === cancellationPending.id}
            onClick={() => void confirmCancellation()}
          >
            {cancelling === cancellationPending?.id ? "Cancelling…" : "Confirm cancellation"}
          </button>
        </div>
      </dialog>
    </main>
  );
}
