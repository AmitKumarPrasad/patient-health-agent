import asyncio

from fastapi.testclient import TestClient
from sqlalchemy.exc import OperationalError
from starlette.requests import Request
from starlette.responses import PlainTextResponse

from app.config import settings
from app.db.session import get_db
from app.main import SecurityHeadersMiddleware, app


client = TestClient(app)


def test_health() -> None:
    response = client.get("/health")

    assert response.status_code == 200
    assert response.json() == {"status": "ok"}
    assert response.headers["X-Content-Type-Options"] == "nosniff"
    assert response.headers["X-Frame-Options"] == "DENY"
    assert response.headers["Referrer-Policy"] == "strict-origin-when-cross-origin"
    assert response.headers["Permissions-Policy"] == "camera=(), microphone=(), geolocation=()"
    assert "Strict-Transport-Security" not in response.headers


def test_hsts_is_added_for_production_https_requests(monkeypatch) -> None:
    monkeypatch.setattr(settings, "app_env", "production")
    middleware = SecurityHeadersMiddleware(lambda request: None)
    scope = {
        "type": "http",
        "method": "GET",
        "path": "/api/example",
        "headers": [],
        "query_string": b"",
        "client": ("127.0.0.1", 12345),
        "server": ("testserver", 443),
        "scheme": "https",
        "http_version": "1.1",
    }
    request = Request(scope)

    async def call_next(_request: Request):
        return PlainTextResponse("ok")

    response = asyncio.run(middleware.dispatch(request, call_next))

    assert response.headers["Strict-Transport-Security"] == "max-age=31536000; includeSubDomains"


def test_readiness_reports_ready_when_database_is_reachable() -> None:
    class FakeSession:
        def execute(self, statement):
            assert str(statement) == "SELECT 1"

    app.dependency_overrides[get_db] = lambda: FakeSession()
    try:
        response = client.get("/ready")
    finally:
        app.dependency_overrides.pop(get_db, None)

    assert response.status_code == 200
    assert response.json() == {"status": "ready"}


def test_readiness_reports_not_ready_when_database_is_unreachable() -> None:
    class BrokenSession:
        def execute(self, statement):
            raise OperationalError(statement, {}, Exception("database unavailable"))

    app.dependency_overrides[get_db] = lambda: BrokenSession()
    try:
        response = client.get("/ready")
    finally:
        app.dependency_overrides.pop(get_db, None)

    assert response.status_code == 503
    assert response.json() == {"status": "not_ready", "database": "unreachable"}
