from fastapi.testclient import TestClient

from app.api import agent
from app.main import app


client = TestClient(app)


def test_agent_chat_without_api_key(monkeypatch) -> None:
    def _raise_missing_key(message: str, subject: str) -> str:
        raise RuntimeError("OPENAI_API_KEY is not configured")

    monkeypatch.setattr(agent, "invoke_appointment_agent", _raise_missing_key)
    app.dependency_overrides[agent.get_current_user] = lambda: {
        "sub": "test-patient-subject"
    }
    try:
        response = client.post("/api/agent/chat", json={"message": "I need a dermatologist"})
    finally:
        app.dependency_overrides.pop(agent.get_current_user, None)

    assert response.status_code == 503
    assert "OPENAI_API_KEY" in response.json()["detail"]
