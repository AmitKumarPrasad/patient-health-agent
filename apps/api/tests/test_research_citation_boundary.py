from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.api.research import router
from app.auth.keycloak import get_current_user


def test_public_research_response_filters_unsafe_citations(monkeypatch) -> None:
    """The API must never return unsafe citations even if the agent returns them."""
    app = FastAPI()
    app.include_router(router)
    app.dependency_overrides[get_current_user] = lambda: {
        "sub": "synthetic-research-user",
        "realm_access": {"roles": ["patient"]},
    }
    monkeypatch.setattr(
        "app.api.research.invoke_research_agent",
        lambda _message: {
            "response": "General information from public sources.",
            "sources": [
                {"title": "Public health guidance", "url": "https://example.org/guidance"},
                {"title": "Local service", "url": "http://127.0.0.1/admin"},
                {"title": "Script source", "url": "javascript:alert(1)"},
                {"title": "Credential-bearing source", "url": "https://user:pass@example.org/page"},
            ],
        },
    )

    response = TestClient(app).post(
        "/api/research",
        json={"message": "Explain a general preventive care concept"},
    )

    assert response.status_code == 200
    assert response.json()["response"] == "General information from public sources."
    assert response.json()["sources"] == [
        {"title": "Public health guidance", "url": "https://example.org/guidance"}
    ]
    assert "127.0.0.1" not in response.text
    assert "javascript:" not in response.text
    assert "user:pass" not in response.text
