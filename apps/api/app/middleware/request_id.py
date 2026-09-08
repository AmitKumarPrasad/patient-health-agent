from __future__ import annotations

from time import monotonic
from uuid import uuid4

from fastapi import Request
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import Response


REQUEST_ID_HEADER = "X-Request-ID"
PROCESS_TIME_HEADER = "X-Process-Time-Ms"


class RequestIDMiddleware(BaseHTTPMiddleware):
    """Attach correlation and lightweight request-duration metadata to responses."""

    async def dispatch(self, request: Request, call_next) -> Response:
        request_id = str(uuid4())
        started_at = monotonic()
        request.state.request_id = request_id
        response = await call_next(request)
        elapsed_ms = max(0, round((monotonic() - started_at) * 1000))
        response.headers.setdefault(REQUEST_ID_HEADER, request_id)
        response.headers.setdefault(PROCESS_TIME_HEADER, str(elapsed_ms))
        return response
