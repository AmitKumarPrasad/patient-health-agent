"use client";

import ResearchAssistant from "../research-assistant";
import { useAuth } from "../providers";

export default function ResearchPage() {
  const auth = useAuth();

  if (!auth.ready) {
    return <main className="center"><p>Loading authentication…</p></main>;
  }

  if (!auth.authenticated) {
    return (
      <main className="center">
        <div className="card auth-card">
          <p className="eyebrow">Patient Health Agent</p>
          <h1>Public health research</h1>
          <p className="muted">Sign in to use the public-information research assistant.</p>
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
          <a href="/">Dashboard</a>
          <button className="secondary" onClick={() => void auth.logout()}>Sign out</button>
        </nav>
      </header>
      <div className="container">
        <section className="hero">
          <p className="eyebrow">AI research</p>
          <h1>Public health information</h1>
          <p className="subtitle">
            Research public healthcare topics without sending patient records to the research workflow.
          </p>
        </section>
        <ResearchAssistant />
      </div>
    </main>
  );
}
