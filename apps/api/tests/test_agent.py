from fastapi.testclient import TestClient

from app.api import agent
from app.main import app


client = TestClient(app)


def test_agent_chat_without_api_key(monkeypatch) -> None:
    monkeypatch.setattr(agent, "build_appointment_graph", lambda: _MissingKeyGraph())
    response = client.post("/api/agent/chat", json={"message": "I need a dermatologist"})

    assert response.status_code == 503
    assert "OPENAI_API_KEY" in response.json()["detail"]


class _MissingKeyGraph:
    def invoke(self, state):
        raise RuntimeError("OPENAI_API_KEY is not configured")
