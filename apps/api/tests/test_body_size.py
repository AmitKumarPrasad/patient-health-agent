from fastapi.testclient import TestClient

from app.config import settings
from app.main import app


client = TestClient(app)


def test_request_body_within_limit_is_accepted() -> None:
    response = client.get(
        "/health",
        headers={"Content-Length": str(settings.max_request_body_bytes)},
    )

    assert response.status_code == 200


def test_request_body_over_limit_is_rejected() -> None:
    response = client.post(
        "/health",
        headers={"Content-Length": str(settings.max_request_body_bytes + 1)},
    )

    assert response.status_code == 413
    assert response.json() == {"detail": "Request body too large"}
    assert response.headers["X-Request-ID"]
