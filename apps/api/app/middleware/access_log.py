from __future__ import annotations

import logging
from time import monotonic

from fastapi import Request
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import Response


logger = logging.getLogger("app.access")


class AccessLogMiddleware(BaseHTTPMiddleware):
    """Log request outcome and latency without logging request or response bodies."""

    async def dispatch(self, request: Request, call_next) -> Response:
        started = monotonic()
        response = await call_next(request)
        duration_ms = (monotonic() - started) * 1000
        request_id = getattr(request.state, "request_id", "unknown")
        logger.info(
            "HTTP request method=%s path=%s status=%s duration_ms=%.2f request_id=%s",
            request.method,
            request.url.path,
            response.status_code,
            duration_ms,
            request_id,
        )
        return response
