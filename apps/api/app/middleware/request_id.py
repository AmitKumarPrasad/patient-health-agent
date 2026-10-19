from __future__ import annotations

import logging
from time import monotonic
from uuid import uuid4

from fastapi import Request
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import Response

from app.observability import observe_http_request


logger = logging.getLogger(__name__)
REQUEST_ID_HEADER = "X-Request-ID"
PROCESS_TIME_HEADER = "X-Process-Time-Ms"


class RequestIDMiddleware(BaseHTTPMiddleware):
    """Attach correlation and request observability metadata without request bodies."""

    async def dispatch(self, request: Request, call_next) -> Response:
        request_id = str(uuid4())
        started_at = monotonic()
        request.state.request_id = request_id
        response = await call_next(request)
        elapsed_seconds = max(0.0, monotonic() - started_at)
        elapsed_ms = max(0, round(elapsed_seconds * 1000))
        response.headers.setdefault(REQUEST_ID_HEADER, request_id)
        response.headers.setdefault(PROCESS_TIME_HEADER, str(elapsed_ms))

        route = request.scope.get("route")
        # Never use a raw, unmatched URL as a metric label: clients can send
        # arbitrary paths and create an unbounded number of Prometheus series.
        route_template = getattr(route, "path", "<unmatched>")
        observe_http_request(
            method=request.method,
            route=route_template,
            status_code=response.status_code,
            duration_seconds=elapsed_seconds,
        )
        logger.info(
            "http_request_completed",
            extra={
                "request_id": request_id,
                "method": request.method,
                "route": route_template,
                "status_code": response.status_code,
                "duration_ms": elapsed_ms,
            },
        )
        return response
