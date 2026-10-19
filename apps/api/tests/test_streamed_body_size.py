import asyncio
import json

from app.config import settings
from app.middleware.body_size import RequestBodySizeLimitMiddleware


def _scope() -> dict:
    return {
        "type": "http",
        "asgi": {"version": "3.0"},
        "http_version": "1.1",
        "method": "POST",
        "scheme": "http",
        "path": "/api/upload",
        "raw_path": b"/api/upload",
        "query_string": b"",
        "headers": [(b"host", b"testserver")],
        "client": ("127.0.0.1", 12345),
        "server": ("testserver", 80),
        "state": {"request_id": "test-request-id"},
    }


def _request_messages(*chunks: bytes) -> list[dict]:
    return [
        {
            "type": "http.request",
            "body": chunk,
            "more_body": index < len(chunks) - 1,
        }
        for index, chunk in enumerate(chunks)
    ]


def test_streamed_request_within_limit_reaches_app_unchanged(monkeypatch) -> None:
    monkeypatch.setattr(settings, "max_request_body_bytes", 5)
    messages = _request_messages(b"123", b"45")
    received_body = bytearray()
    response_messages: list[dict] = []
    app_called = False

    async def receive() -> dict:
        if messages:
            return messages.pop(0)
        return {"type": "http.disconnect"}

    async def app(scope, app_receive, send) -> None:
        nonlocal app_called
        app_called = True
        while True:
            message = await app_receive()
            if message["type"] == "http.disconnect":
                break
            received_body.extend(message.get("body", b""))
            if not message.get("more_body", False):
                break
        await send({"type": "http.response.start", "status": 200, "headers": []})
        await send({"type": "http.response.body", "body": b"ok"})

    async def run() -> None:
        await RequestBodySizeLimitMiddleware(app)(_scope(), receive, response_messages.append)

    asyncio.run(run())

    assert app_called
    assert bytes(received_body) == b"12345"
    assert response_messages[0]["status"] == 200


def test_streamed_request_over_limit_returns_413_without_calling_app(monkeypatch) -> None:
    monkeypatch.setattr(settings, "max_request_body_bytes", 5)
    messages = _request_messages(b"123", b"456")
    response_messages: list[dict] = []
    app_called = False

    async def receive() -> dict:
        if messages:
            return messages.pop(0)
        return {"type": "http.disconnect"}

    async def app(scope, app_receive, send) -> None:
        nonlocal app_called
        app_called = True

    async def send(message: dict) -> None:
        response_messages.append(message)

    async def run() -> None:
        await RequestBodySizeLimitMiddleware(app)(_scope(), receive, send)

    asyncio.run(run())

    assert not app_called
    assert response_messages[0]["status"] == 413
    assert response_messages[0]["headers"][-1] == (b"x-request-id", b"test-request-id")
    assert json.loads(response_messages[1]["body"]) == {"detail": "Request body too large"}
