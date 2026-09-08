import asyncio

from starlette.requests import Request
from starlette.responses import PlainTextResponse

from app.config import settings
from app.middleware.rate_limit import FixedWindowRateLimitMiddleware, MAX_TRACKED_CLIENTS


def _request(path: str, host: str = "127.0.0.1", forwarded_for: str | None = None) -> Request:
    headers = []
    if forwarded_for is not None:
        headers.append((b"x-forwarded-for", forwarded_for.encode()))
    scope = {
        "type": "http",
        "method": "GET",
        "path": path,
        "headers": headers,
        "query_string": b"",
        "client": (host, 12345),
        "server": ("testserver", 80),
        "scheme": "http",
        "http_version": "1.1",
    }
    return Request(scope)


def test_rate_limit_returns_429_after_threshold(monkeypatch) -> None:
    monkeypatch.setattr(settings, "rate_limit_requests", 1)
    monkeypatch.setattr(settings, "rate_limit_window_seconds", 60)
    middleware = FixedWindowRateLimitMiddleware(lambda request: None)

    async def run() -> list[int]:
        statuses: list[int] = []

        async def call_next(request):
            return PlainTextResponse("ok")

        for _ in range(2):
            request = _request("/api/example")
            response = await middleware.dispatch(request, call_next)
            statuses.append(response.status_code)
        return statuses

    assert asyncio.run(run()) == [200, 429]


def test_health_check_is_exempt_from_rate_limit(monkeypatch) -> None:
    monkeypatch.setattr(settings, "rate_limit_requests", 1)
    middleware = FixedWindowRateLimitMiddleware(lambda request: None)

    async def run() -> list[int]:
        statuses: list[int] = []

        async def call_next(request):
            return PlainTextResponse("ok")

        for _ in range(2):
            statuses.append((await middleware.dispatch(_request("/health"), call_next)).status_code)
        return statuses

    assert asyncio.run(run()) == [200, 200]


def test_rate_limit_state_is_bounded(monkeypatch) -> None:
    import app.middleware.rate_limit as rate_limit

    monkeypatch.setattr(settings, "rate_limit_requests", 10)
    monkeypatch.setattr(settings, "rate_limit_window_seconds", 60)
    monkeypatch.setattr(rate_limit, "MAX_TRACKED_CLIENTS", 2)
    middleware = FixedWindowRateLimitMiddleware(lambda request: None)

    async def run() -> None:
        async def call_next(request):
            return PlainTextResponse("ok")

        for host in ("10.0.0.1", "10.0.0.2", "10.0.0.3"):
            await middleware.dispatch(_request("/api/example", host), call_next)

    asyncio.run(run())

    assert len(middleware._windows) <= 2
    assert len(middleware._windows) <= MAX_TRACKED_CLIENTS


def test_rate_limit_removes_stale_clients_before_capacity_eviction(monkeypatch) -> None:
    import app.middleware.rate_limit as rate_limit

    monkeypatch.setattr(settings, "rate_limit_requests", 10)
    monkeypatch.setattr(settings, "rate_limit_window_seconds", 60)
    monkeypatch.setattr(rate_limit, "MAX_TRACKED_CLIENTS", 2)
    monkeypatch.setattr(rate_limit, "monotonic", lambda: 200.0)
    middleware = FixedWindowRateLimitMiddleware(lambda request: None)
    middleware._windows["10.0.0.1"] = (1, 100.0)
    middleware._windows["10.0.0.2"] = (1, 199.0)

    async def run() -> None:
        async def call_next(request):
            return PlainTextResponse("ok")

        await middleware.dispatch(_request("/api/example", "10.0.0.3"), call_next)

    asyncio.run(run())

    assert "10.0.0.1" not in middleware._windows
    assert "10.0.0.2" in middleware._windows
    assert "10.0.0.3" in middleware._windows


def test_forwarded_for_is_ignored_by_default(monkeypatch) -> None:
    monkeypatch.setattr(settings, "rate_limit_trust_forwarded_for", False)
    request = _request("/api/example", host="10.0.0.1", forwarded_for="192.0.2.10")

    assert FixedWindowRateLimitMiddleware._client_key(request) == "10.0.0.1"


def test_first_forwarded_for_hop_is_used_when_trusted(monkeypatch) -> None:
    monkeypatch.setattr(settings, "rate_limit_trust_forwarded_for", True)
    request = _request(
        "/api/example",
        host="10.0.0.1",
        forwarded_for="192.0.2.10, 198.51.100.4",
    )

    assert FixedWindowRateLimitMiddleware._client_key(request) == "192.0.2.10"
