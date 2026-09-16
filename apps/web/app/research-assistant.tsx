"use client";

import { FormEvent, useState } from "react";
import { api } from "../lib/api";

export default function ResearchAssistant() {
  const [message, setMessage] = useState("");
  const [answer, setAnswer] = useState("");
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
      setMessage("");
    } catch (err) {
      setError(err instanceof Error ? err.message : "Research request failed");
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
        <div className="chat-answer" style={{ marginTop: 12, whiteSpace: "pre-wrap" }}>
          {answer}
        </div>
      )}
    </section>
  );
}
