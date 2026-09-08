import asyncio
import logging

from starlette.requests import Request
from starlette.responses import PlainTextResponse

from app.middleware.access_log import AccessLogMiddleware


def _request() -> Request:
    return Request(
        {
            "type": "http",
            "method": "GET",
            "path": "/health",
            "headers": [],
            "query_string": b"",
            "client": ("127.0.0.1", 12345),
            "server": ("testserver", 80),
            "scheme": "http",
            "http_version": "1.1",
        }
    )


def test_access_log_includes_request_id_status_and_latency(caplog) -> None:
    middleware = AccessLogMiddleware(lambda request: None)

    async def run() -> None:
        async def call_next(request):
            request.state.request_id = "test-request-id"
            return PlainTextResponse("ok", status_code=201)

        response = await middleware.dispatch(_request(), call_next)
        assert response.status_code == 201

    with caplog.at_level(logging.INFO, logger="app.access"):
        asyncio.run(run())

    message = next(record.getMessage() for record in caplog.records if record.name == "app.access")
    assert "method=GET" in message
    assert "path=/health" in message
    assert "status=201" in message
    assert "request_id=test-request-id" in message
    assert "duration_ms=" in message


def test_access_log_does_not_log_request_body(caplog) -> None:
    middleware = AccessLogMiddleware(lambda request: None)

    async def run() -> None:
        async def call_next(request):
            request.state.request_id = "test-request-id"
            return PlainTextResponse("sensitive-response-body")

        await middleware.dispatch(_request(), call_next)

    with caplog.at_level(logging.INFO, logger="app.access"):
        asyncio.run(run())

    assert all("sensitive-response-body" not in record.getMessage() for record in caplog.records)
