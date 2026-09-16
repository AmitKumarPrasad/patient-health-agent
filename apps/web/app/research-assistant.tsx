"use client";

import { FormEvent, useState } from "react";
import { api, ResearchSource } from "../lib/api";

function SourceList({ sources }: { sources: ResearchSource[] }) {
  if (!sources.length) return null;
  return (
    <div style={{ marginTop: 18 }}>
      <h3>Sources</h3>
      <ol>
        {sources.map((source) => (
          <li key={source.url} style={{ marginBottom: 8 }}>
            <a href={source.url} target="_blank" rel="noreferrer">
              {source.title}
            </a>
          </li>
        ))}
      </ol>
    </div>
  );
}

export default function ResearchAssistant() {
  const [message, setMessage] = useState("");
  const [answer, setAnswer] = useState("");
  const [sources, setSources] = useState<ResearchSource[]>([]);
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(false);

  async function submit(event: FormEvent) {
    event.preventDefault();
    const question = message.trim();
    if (!question) return;

    setLoading(true);
    setError("");
    try {
      const result = await api.research(question);
      setAnswer(result.response);
      setSources(result.sources);
      setMessage("");
    } catch (err) {
      setError(err instanceof Error ? err.message : "Research request failed");
      setSources([]);
    } finally {
      setLoading(false);
    }
  }

  return (
    <section className="card full" id="research">
      <h2>Public health research assistant</h2>
      <p className="muted">
        Ask about public healthcare information, terminology, workflows, or standards. This assistant
        searches public sources and is not a diagnostic or treatment tool.
      </p>
      <form className="chat" onSubmit={submit}>
        <textarea
          value={message}
          onChange={(event) => setMessage(event.target.value)}
          placeholder="e.g. What is the difference between preventive and screening care?"
          maxLength={2000}
          disabled={loading}
        />
        <button disabled={loading || !message.trim()}>
          {loading ? "Researching…" : "Research"}
        </button>
      </form>
      {error && <div className="error" style={{ marginTop: 12 }}>{error}</div>}
      {answer && (
        <div className="chat-answer" style={{ marginTop: 12 }}>
          <div style={{ whiteSpace: "pre-wrap" }}>{answer}</div>
          <SourceList sources={sources} />
        </div>
      )}
    </section>
  );
}
