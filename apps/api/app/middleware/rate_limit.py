from __future__ import annotations

from collections import defaultdict
from threading import Lock
from time import monotonic

from fastapi import Request
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware

from app.config import settings


MAX_TRACKED_CLIENTS = 10_000


class FixedWindowRateLimitMiddleware(BaseHTTPMiddleware):
    """Apply a small per-client fixed-window request limit at the API boundary."""

    def __init__(self, app) -> None:
        super().__init__(app)
        self._lock = Lock()
        self._windows: dict[str, tuple[int, float]] = defaultdict(lambda: (0, 0.0))

    async def dispatch(self, request: Request, call_next):
        if settings.rate_limit_requests <= 0 or request.method == "OPTIONS" or request.url.path == "/health":
            return await call_next(request)

        client_host = request.client.host if request.client is not None else "unknown"
        now = monotonic()
        window_seconds = settings.rate_limit_window_seconds

        with self._lock:
            count, window_started = self._windows[client_host]
            if now - window_started >= window_seconds:
                count = 0
                window_started = now

            if count >= settings.rate_limit_requests:
                retry_after = max(1, int(window_seconds - (now - window_started)))
                return JSONResponse(
                    status_code=429,
                    content={"detail": "Rate limit exceeded"},
                    headers={"Retry-After": str(retry_after)},
                )

            self._windows[client_host] = (count + 1, window_started)
            if len(self._windows) > MAX_TRACKED_CLIENTS:
                cutoff = now - window_seconds
                stale_clients = [
                    client for client, (_, started) in self._windows.items() if started < cutoff
                ]
                for client in stale_clients:
                    self._windows.pop(client, None)

                if len(self._windows) > MAX_TRACKED_CLIENTS:
                    oldest_client = min(self._windows, key=lambda client: self._windows[client][1])
                    self._windows.pop(oldest_client, None)

        return await call_next(request)
