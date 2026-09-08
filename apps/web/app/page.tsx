"use client";

import { FormEvent, useEffect, useState } from "react";
import { api, Appointment, Availability, Patient, Provider } from "../lib/api";
import { useAuth } from "./providers";

function formatDate(value: string) {
  return new Intl.DateTimeFormat("en-IN", {
    dateStyle: "medium",
    timeStyle: "short",
  }).format(new Date(value));
}

export default function Home() {
  const auth = useAuth();
  const [patient, setPatient] = useState<Patient | null>(null);
  const [appointments, setAppointments] = useState<Appointment[]>([]);
  const [providers, setProviders] = useState<Provider[]>([]);
  const [availability, setAvailability] = useState<Availability[]>([]);
  const [specialty, setSpecialty] = useState("");
  const [selectedProvider, setSelectedProvider] = useState<Provider | null>(null);
  const [date, setDate] = useState(() => new Date().toISOString().slice(0, 10));
  const [reason, setReason] = useState("");
  const [message, setMessage] = useState("");
  const [answer, setAnswer] = useState("");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");

  useEffect(() => {
    if (!auth.ready || !auth.authenticated) return;
    void loadDashboard();
  }, [auth.ready, auth.authenticated]);

  async function loadDashboard() {
    setLoading(true);
    setError("");
    try {
      const [me, upcoming] = await Promise.all([api.me(), api.appointments()]);
      setPatient(me);
      setAppointments(upcoming);
      setProviders(await api.providers());
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
          <a href="#providers">Providers</a>
          <a href="#assistant">AI Assistant</a>
          <button className="secondary" onClick={() => void auth.logout()}>Sign out</button>
        </nav>
      </header>

      <div className="container">
        <section className="hero">
          <p className="eyebrow">Patient dashboard</p>
          <h1>Welcome{patient ? `, ${patient.first_name}` : ""}</h1>
          <p className="subtitle">Manage appointments and use the assistant for scheduling workflows. The AI does not provide clinical diagnosis or treatment decisions.</p>
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
