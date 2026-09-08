from uuid import UUID

from fastapi.testclient import TestClient

from app.main import app
from app.middleware.request_id import REQUEST_ID_HEADER


client = TestClient(app)


def test_request_id_header_is_returned() -> None:
    response = client.get("/health")

    request_id = response.headers.get(REQUEST_ID_HEADER)
    assert response.status_code == 200
    assert request_id is not None
    UUID(request_id)


def test_request_id_is_generated_per_request() -> None:
    first = client.get("/health").headers[REQUEST_ID_HEADER]
    second = client.get("/health").headers[REQUEST_ID_HEADER]

    assert first != second
    UUID(first)
    UUID(second)
