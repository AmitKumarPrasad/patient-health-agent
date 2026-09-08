from starlette.requests import Request
from starlette.responses import PlainTextResponse

from app.config import settings
from app.middleware.rate_limit import FixedWindowRateLimitMiddleware


async def _ok_endpoint(scope, receive, send) -> None:
    response = PlainTextResponse("ok")
    await response(scope, receive, send)


def _request(path: str, host: str = "127.0.0.1") -> Request:
    scope = {
        "type": "http",
        "method": "GET",
        "path": path,
        "headers": [],
        "query_string": b"",
        "client": (host, 12345),
        "server": ("testserver", 80),
        "scheme": "http",
        "http_version": "1.1",
    }
    return Request(scope)


def test_rate_limit_returns_429_after_threshold(monkeypatch) -> None:
    import asyncio

    monkeypatch.setattr(settings, "rate_limit_requests", 1)
    monkeypatch.setattr(settings, "rate_limit_window_seconds", 60)
    middleware = FixedWindowRateLimitMiddleware(_ok_endpoint)

    async def run() -> list[int]:
        statuses: list[int] = []

        async def call_next(request):
            response = await _ok_endpoint(request.scope, request.receive, request._send)
            return response

        for _ in range(2):
            request = _request("/api/example")
            response = await middleware.dispatch(request, call_next)
            statuses.append(response.status_code)
        return statuses

    assert asyncio.run(run()) == [200, 429]


def test_health_check_is_exempt_from_rate_limit(monkeypatch) -> None:
    import asyncio

    monkeypatch.setattr(settings, "rate_limit_requests", 1)
    middleware = FixedWindowRateLimitMiddleware(_ok_endpoint)

    async def run() -> list[int]:
        statuses: list[int] = []

        async def call_next(request):
            return PlainTextResponse("ok")

        for _ in range(2):
            statuses.append((await middleware.dispatch(_request("/health"), call_next)).status_code)
        return statuses

    assert asyncio.run(run()) == [200, 200]
