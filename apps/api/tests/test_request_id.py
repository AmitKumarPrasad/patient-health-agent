from uuid import UUID

from fastapi.testclient import TestClient

from app.main import app
from app.middleware.request_id import PROCESS_TIME_HEADER, REQUEST_ID_HEADER


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


def test_request_id_header_is_returned_on_error_response() -> None:
    response = client.get("/route-that-does-not-exist")

    request_id = response.headers.get(REQUEST_ID_HEADER)
    assert response.status_code == 404
    assert request_id is not None
    UUID(request_id)


def test_request_id_header_is_returned_on_unhandled_exception() -> None:
    path = "/test-request-id-unhandled-exception"

    def raise_error() -> None:
        raise RuntimeError("test failure")

    app.add_api_route(path, raise_error, methods=["GET"])
    try:
        with TestClient(app, raise_server_exceptions=False) as error_client:
            response = error_client.get(path)
    finally:
        app.router.routes[:] = [route for route in app.router.routes if getattr(route, "path", None) != path]

    request_id = response.headers.get(REQUEST_ID_HEADER)
    assert response.status_code == 500
    assert response.json() == {"detail": "Internal server error"}
    assert request_id is not None
    UUID(request_id)


def test_process_time_header_is_returned_and_non_negative() -> None:
    response = client.get("/health")

    process_time = response.headers.get(PROCESS_TIME_HEADER)
    assert response.status_code == 200
    assert process_time is not None
    assert process_time.isdigit()
    assert int(process_time) >= 0
