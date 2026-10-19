import asyncio

from starlette.requests import Request
from starlette.responses import PlainTextResponse

from app.middleware.request_id import RequestIDMiddleware


def _request(path: str) -> Request:
    return Request(
        {
            "type": "http",
            "method": "GET",
            "path": path,
            "headers": [],
            "query_string": b"",
            "client": ("127.0.0.1", 12345),
            "server": ("testserver", 80),
            "scheme": "http",
            "http_version": "1.1",
        }
    )


def test_unmatched_paths_share_a_bounded_metrics_route_label(monkeypatch) -> None:
    import app.middleware.request_id as request_id_module

    observed_routes: list[str] = []
    monkeypatch.setattr(
        request_id_module,
        "observe_http_request",
        lambda **kwargs: observed_routes.append(kwargs["route"]),
    )
    middleware = RequestIDMiddleware(lambda scope, receive, send: None)

    async def call_next(_request: Request) -> PlainTextResponse:
        return PlainTextResponse("not found", status_code=404)

    async def run() -> None:
        await middleware.dispatch(_request("/missing/one"), call_next)
        await middleware.dispatch(_request("/missing/two"), call_next)

    asyncio.run(run())

    assert observed_routes == ["<unmatched>", "<unmatched>"]
