"use client";

import { FormEvent, useEffect, useState } from "react";
import { api, ResearchMessage, ResearchSession, ResearchSessionSummary, ResearchSource } from "../lib/api";

function SourceList({ sources }: { sources: ResearchSource[] }) {
  if (!sources.length) return null;
  return <div style={{ marginTop: 12 }}><strong>Sources</strong><ol>{sources.map((source) => <li key={source.url} style={{ marginBottom: 6 }}><a href={source.url} target="_blank" rel="noreferrer">{source.title}</a></li>)}</ol></div>;
}

function MessageBubble({ message }: { message: ResearchMessage }) {
  return <div className="chat-answer" style={{ marginTop: 10, marginLeft: message.role === "user" ? "12%" : 0 }}><strong>{message.role === "user" ? "You" : "Research assistant"}</strong><div style={{ whiteSpace: "pre-wrap", marginTop: 6 }}>{message.content}</div>{message.role === "assistant" && <SourceList sources={message.sources} />}</div>;
}

export default function ResearchAssistant() {
  const [sessions, setSessions] = useState<ResearchSessionSummary[]>([]);
  const [session, setSession] = useState<ResearchSession | null>(null);
  const [message, setMessage] = useState("");
  const [historyQuery, setHistoryQuery] = useState("");
  const [searchingHistory, setSearchingHistory] = useState(false);
  const [loading, setLoading] = useState(false);
  const [initializing, setInitializing] = useState(true);
  const [error, setError] = useState("");

  useEffect(() => { void loadSessions(); }, []);

  async function loadSessions() {
    try {
      const items = await api.researchSessions();
      setSessions(items);
      if (items.length) setSession(await api.researchSession(items[0].id));
      else setSession(await api.createResearchSession());
    } catch (err) { setError(err instanceof Error ? err.message : "Unable to load research sessions"); }
    finally { setInitializing(false); }
  }

  async function searchHistory(event: FormEvent) {
    event.preventDefault();
    setError("");
    setSearchingHistory(true);
    try {
      const items = await api.researchSessions(historyQuery);
      setSessions(items);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Unable to search research history");
    } finally {
      setSearchingHistory(false);
    }
  }

  async function clearHistorySearch() {
    setHistoryQuery("");
    setError("");
    setSearchingHistory(true);
    try {
      setSessions(await api.researchSessions());
    } catch (err) {
      setError(err instanceof Error ? err.message : "Unable to refresh research history");
    } finally {
      setSearchingHistory(false);
    }
  }

  async function newSession() {
    setError("");
    try {
      const created = await api.createResearchSession();
      setSession(created);
      setHistoryQuery("");
      setSessions((current) => [created, ...current]);
      setMessage("");
    } catch (err) { setError(err instanceof Error ? err.message : "Unable to create session"); }
  }

  async function selectSession(id: string) {
    setError("");
    try { setSession(await api.researchSession(id)); }
    catch (err) { setError(err instanceof Error ? err.message : "Unable to load session"); }
  }

  async function renameSession(item: ResearchSessionSummary) {
    const input = window.prompt("Rename research conversation", item.title);
    if (input === null) return;
    const title = input.trim();
    if (!title || title.length > 200) {
      setError("Research title must be between 1 and 200 characters.");
      return;
    }
    setError("");
    try {
      const updated = await api.renameResearchSession(item.id, title);
      setSessions((current) => current.map((entry) => entry.id === item.id ? updated : entry).sort((a, b) => b.updated_at.localeCompare(a.updated_at)));
      setSession((current) => current?.id === item.id ? updated : current);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Unable to rename research session");
    }
  }

  async function deleteSession(id: string) {
    if (!window.confirm("Delete this research conversation permanently?")) return;
    setError("");
    try {
      await api.deleteResearchSession(id);
      const remaining = sessions.filter((item) => item.id !== id);
      setSessions(remaining);
      if (session?.id === id) {
        setSession(remaining.length ? await api.researchSession(remaining[0].id) : null);
      }
    } catch (err) {
      setError(err instanceof Error ? err.message : "Unable to delete research session");
    }
  }

  async function submit(event: FormEvent) {
    event.preventDefault();
    const question = message.trim();
    if (!question || !session) return;
    setLoading(true); setError("");
    try {
      const updated = await api.sendResearchMessage(session.id, question);
      setSession(updated);
      setSessions((current) => current.map((item) => item.id === updated.id ? updated : item).sort((a, b) => b.updated_at.localeCompare(a.updated_at)));
      setMessage("");
    } catch (err) { setError(err instanceof Error ? err.message : "Research request failed"); }
    finally { setLoading(false); }
  }

  if (initializing) return <section className="card full" id="research"><h2>Public health research assistant</h2><p className="muted">Loading your research sessions…</p></section>;

  return <section className="card full" id="research">
    <div style={{ display: "flex", justifyContent: "space-between", gap: 12, alignItems: "center" }}>
      <div><h2>Public health research assistant</h2><p className="muted">Ask about public healthcare information, terminology, workflows, or standards. Do not enter patient-specific health information.</p></div>
      <button type="button" onClick={newSession}>New research</button>
    </div>
    <div style={{ display: "grid", gridTemplateColumns: "minmax(180px, 28%) 1fr", gap: 16, marginTop: 16 }}>
      <aside><strong>History</strong><form onSubmit={searchHistory} style={{ marginTop: 8 }}><input type="search" aria-label="Search research history" placeholder="Search conversation titles" value={historyQuery} maxLength={100} onChange={(event) => setHistoryQuery(event.target.value)} /><div style={{ display: "flex", gap: 6, marginTop: 6 }}><button type="submit" disabled={searchingHistory}>{searchingHistory ? "Searching…" : "Search"}</button><button type="button" onClick={() => void clearHistorySearch()} disabled={searchingHistory}>Clear</button></div></form>{sessions.length === 0 && <p className="muted">No matching conversations.</p>}{sessions.map((item) => <div key={item.id} style={{ display: "flex", gap: 4, marginTop: 8 }}><button type="button" onClick={() => void selectSession(item.id)} style={{ flex: 1, minWidth: 0, textAlign: "left", overflow: "hidden", textOverflow: "ellipsis" }}>{item.title}</button><button type="button" aria-label={`Rename ${item.title}`} title="Rename research conversation" onClick={() => void renameSession(item)}>Rename</button><button type="button" aria-label={`Delete ${item.title}`} title="Delete research conversation" onClick={() => void deleteSession(item.id)}>Delete</button></div>)}</aside>
      <div>
        <div style={{ minHeight: 180 }}>{session?.messages.length ? session.messages.map((item) => <MessageBubble key={item.id} message={item} />) : <p className="muted">Start a research conversation. Your session history is private to your authenticated account.</p>}</div>
        <form className="chat" onSubmit={submit}>
          <textarea value={message} onChange={(event) => setMessage(event.target.value)} placeholder="e.g. What is the difference between preventive and screening care?" maxLength={2000} disabled={loading || !session} />
          <button disabled={loading || !message.trim() || !session}>{loading ? "Researching…" : "Research"}</button>
        </form>
      </div>
    </div>
    {error && <div className="error" style={{ marginTop: 12 }}>{error}</div>}
  </section>;
}
