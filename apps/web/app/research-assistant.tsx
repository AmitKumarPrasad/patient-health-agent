"use client";

import { FormEvent, useEffect, useState } from "react";
import { api, ResearchMessage, ResearchSession, ResearchSessionSummary, ResearchSource } from "../lib/api";

function SourceList({ sources }: { sources: ResearchSource[] }) {
  const safeSources = sources.filter((source) => /^https?:\/\//i.test(source.url) && !/[\s\\]/.test(source.url));
  if (!safeSources.length) return null;
  return <div style={{ marginTop: 12 }}><strong>Sources</strong><ol>{safeSources.map((source) => <li key={source.url} style={{ marginBottom: 6 }}><a href={source.url} target="_blank" rel="noreferrer">{source.title}</a></li>)}</ol></div>;
}

function MessageBubble({ message }: { message: ResearchMessage }) {
  return <div className="chat-answer" style={{ marginTop: 10, marginLeft: message.role === "user" ? "12%" : 0 }}><strong>{message.role === "user" ? "You" : "Research assistant"}</strong><div style={{ whiteSpace: "pre-wrap", marginTop: 6 }}>{message.content}</div>{message.role === "assistant" && <SourceList sources={message.sources} />}</div>;
}

export default function ResearchAssistant() {
  const [sessions, setSessions] = useState<ResearchSessionSummary[]>([]);
  const [session, setSession] = useState<ResearchSession | null>(null);
  const [message, setMessage] = useState("");
  const [historyQuery, setHistoryQuery] = useState("");
  const [appliedQuery, setAppliedQuery] = useState("");
  const [historyPage, setHistoryPage] = useState(0);
  const [hasNextPage, setHasNextPage] = useState(false);
  const pageSize = 20;
  const [searchingHistory, setSearchingHistory] = useState(false);
  const [loading, setLoading] = useState(false);
  const [initializing, setInitializing] = useState(true);
  const [error, setError] = useState("");

  useEffect(() => { void loadSessions(); }, []);

  async function loadSessions() {
    setInitializing(true);
    setError("");
    try {
      const items = await api.researchSessions();
      setHasNextPage(items.length === pageSize);
      if (items.length) {
        setSessions(items);
        setSession(await api.researchSession(items[0].id));
      } else {
        const created = await api.createResearchSession();
        setSessions([created]);
        setSession(created);
      }
    } catch (err) { setError(err instanceof Error ? err.message : "Unable to load research sessions"); }
    finally { setInitializing(false); }
  }

  async function searchHistory(event: FormEvent) {
    event.preventDefault();
    setError("");
    setSearchingHistory(true);
    try {
      const query = historyQuery.trim();
      const items = await api.researchSessions(query, 0, pageSize);
      setAppliedQuery(query);
      setHistoryPage(0);
      setHasNextPage(items.length === pageSize);
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
      const items = await api.researchSessions("", 0, pageSize);
      setAppliedQuery("");
      setHistoryPage(0);
      setHasNextPage(items.length === pageSize);
      setSessions(items);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Unable to refresh research history");
    } finally {
      setSearchingHistory(false);
    }
  }

  async function changeHistoryPage(nextPage: number) {
    if (nextPage < 0) return;
    setError("");
    setSearchingHistory(true);
    try {
      const items = await api.researchSessions(appliedQuery, nextPage * pageSize, pageSize);
      setHistoryPage(nextPage);
      setHasNextPage(items.length === pageSize);
      setSessions(items);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Unable to load research history page");
    } finally {
      setSearchingHistory(false);
    }
  }

  async function newSession() {
    setError("");
    try {
      const created = await api.createResearchSession();
      setSession(created);
      setSessions((current) => [created, ...current].slice(0, pageSize));
      setHistoryQuery("");
      setAppliedQuery("");
      setHistoryPage(0);
      setMessage("");
      try {
        const items = await api.researchSessions("", 0, pageSize);
        setHasNextPage(items.length === pageSize);
        setSessions(items);
      } catch {
        // Keep the newly created conversation usable when history refresh fails.
      }
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
      let remaining = sessions.filter((item) => item.id !== id);
      if (session?.id === id) {
        if (!remaining.length) {
          setHistoryQuery("");
          setAppliedQuery("");
          setHistoryPage(0);
          remaining = await api.researchSessions("", 0, pageSize);
          if (!remaining.length) {
            const created = await api.createResearchSession();
            remaining = [created];
            setSession(created);
          } else {
            setSession(await api.researchSession(remaining[0].id));
          }
          setHasNextPage(remaining.length === pageSize);
        } else {
          setSession(await api.researchSession(remaining[0].id));
        }
      }
      setSessions(remaining);
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
      <aside><strong>History</strong><form onSubmit={searchHistory} style={{ marginTop: 8 }}><input type="search" aria-label="Search research history" placeholder="Search conversation titles" value={historyQuery} maxLength={100} onChange={(event) => setHistoryQuery(event.target.value)} /><div style={{ display: "flex", gap: 6, marginTop: 6 }}><button type="submit" disabled={searchingHistory}>{searchingHistory ? "Searching…" : "Search"}</button><button type="button" onClick={() => void clearHistorySearch()} disabled={searchingHistory}>Clear</button></div></form>{sessions.length === 0 && <p className="muted">No matching conversations.</p>}{sessions.map((item) => <div key={item.id} style={{ display: "flex", gap: 4, marginTop: 8 }}><button type="button" onClick={() => void selectSession(item.id)} style={{ flex: 1, minWidth: 0, textAlign: "left", overflow: "hidden", textOverflow: "ellipsis" }}>{item.title}</button><button type="button" aria-label={`Rename ${item.title}`} title="Rename research conversation" onClick={() => void renameSession(item)}>Rename</button><button type="button" aria-label={`Delete ${item.title}`} title="Delete research conversation" onClick={() => void deleteSession(item.id)}>Delete</button></div>)}<div style={{ display: "flex", gap: 6, alignItems: "center", marginTop: 12 }}><button type="button" disabled={searchingHistory || historyPage === 0} onClick={() => void changeHistoryPage(historyPage - 1)}>Previous</button><span aria-live="polite">Page {historyPage + 1}</span><button type="button" disabled={searchingHistory || !hasNextPage} onClick={() => void changeHistoryPage(historyPage + 1)}>Next</button></div></aside>
      <div>
        <div
          role="log"
          aria-label="Research conversation"
          aria-live="polite"
          aria-relevant="additions text"
          aria-busy={loading}
          style={{ minHeight: 180 }}
        >{session?.messages.length ? session.messages.map((item) => <MessageBubble key={item.id} message={item} />) : <p className="muted">Start a research conversation. Your session history is private to your authenticated account.</p>}</div>
        <form className="chat" onSubmit={submit}>
          <textarea value={message} onChange={(event) => setMessage(event.target.value)} placeholder="e.g. What is the difference between preventive and screening care?" maxLength={2000} disabled={loading || !session} />
          <button disabled={loading || !message.trim() || !session}>{loading ? "Researching…" : "Research"}</button>
        </form>
      </div>
    </div>
    {error && <div className="error" role="alert" style={{ marginTop: 12 }}>{error}{!session && <button type="button" onClick={() => void loadSessions()} style={{ marginLeft: 12 }}>Retry loading conversations</button>}</div>}
  </section>;
}
