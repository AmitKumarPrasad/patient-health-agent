from __future__ import annotations

from fastapi.responses import JSONResponse

from app.config import settings
from app.middleware.request_id import REQUEST_ID_HEADER


class RequestBodySizeLimitMiddleware:
    """Enforce the API body limit for both declared and streamed request bodies."""

    def __init__(self, app) -> None:
        self.app = app

    async def __call__(self, scope, receive, send) -> None:
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return

        content_length_header = next(
            (
                value.decode("latin-1")
                for name, value in scope.get("headers", [])
                if name.lower() == b"content-length"
            ),
            None,
        )
        if content_length_header is not None:
            try:
                declared_size = int(content_length_header)
            except ValueError:
                declared_size = None
            if declared_size is not None:
                if declared_size > settings.max_request_body_bytes:
                    await self._reject_oversized(scope, receive, send)
                    return
                await self.app(scope, receive, send)
                return

        buffered_messages = []
        total_size = 0
        while True:
            message = await receive()
            buffered_messages.append(message)
            if message["type"] == "http.request":
                total_size += len(message.get("body", b""))
                if total_size > settings.max_request_body_bytes:
                    await self._reject_oversized(scope, receive, send)
                    return
                if not message.get("more_body", False):
                    break
            elif message["type"] == "http.disconnect":
                break

        message_index = 0

        async def replay_receive():
            nonlocal message_index
            if message_index < len(buffered_messages):
                message = buffered_messages[message_index]
                message_index += 1
                return message
            return await receive()

        await self.app(scope, replay_receive, send)

    @staticmethod
    async def _reject_oversized(scope, receive, send) -> None:
        request_id = scope.get("state", {}).get("request_id", "unknown")
        response = JSONResponse(
            status_code=413,
            content={"detail": "Request body too large"},
            headers={REQUEST_ID_HEADER: request_id},
        )
        await response(scope, receive, send)
