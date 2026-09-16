from __future__ import annotations

from fastapi import Request
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware

from app.config import settings
from app.middleware.request_id import REQUEST_ID_HEADER


class RequestBodySizeLimitMiddleware(BaseHTTPMiddleware):
    """Reject requests whose declared body exceeds the API boundary limit."""

    async def dispatch(self, request: Request, call_next):
        content_length = request.headers.get("content-length")
        if content_length is not None:
            try:
                size = int(content_length)
            except ValueError:
                size = None
            if size is not None and size > settings.max_request_body_bytes:
                request_id = getattr(request.state, "request_id", "unknown")
                return JSONResponse(
                    status_code=413,
                    content={"detail": "Request body too large"},
                    headers={REQUEST_ID_HEADER: request_id},
                )
        return await call_next(request)
