from __future__ import annotations

import logging

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response

from app.api.agent import router as agent_router
from app.api.appointments import router as appointments_router
from app.api.audit import router as audit_router
from app.api.clinical import router as clinical_router
from app.api.consultations import router as consultations_router
from app.api.documents import router as documents_router
from app.api.health import router as health_router
from app.api.provider_records import router as provider_records_router
from app.api.records import router as records_router
from app.api.research import router as research_router
from app.config import settings
from app.middleware.access_log import AccessLogMiddleware
from app.middleware.rate_limit import FixedWindowRateLimitMiddleware
from app.middleware.request_id import REQUEST_ID_HEADER, RequestIDMiddleware


logger = logging.getLogger(__name__)

app = FastAPI(
    title=settings.app_name,
    version="0.1.0",
    description="Backend API for the Patient Health Agent platform.",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=[origin.strip() for origin in settings.cors_origins.split(",") if origin.strip()],
    allow_credentials=True,
    allow_methods=["GET", "POST", "PATCH", "DELETE", "OPTIONS"],
    allow_headers=["Authorization", "Content-Type"],
)


@app.exception_handler(Exception)
async def unhandled_exception_handler(request: Request, exc: Exception) -> JSONResponse:
    request_id = getattr(request.state, "request_id", "unknown")
    logger.exception("Unhandled API exception request_id=%s", request_id)
    return JSONResponse(
        status_code=500,
        content={"detail": "Internal server error"},
        headers={REQUEST_ID_HEADER: request_id},
    )


class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next) -> Response:
        response = await call_next(request)
        response.headers.setdefault("X-Content-Type-Options", "nosniff")
        response.headers.setdefault("X-Frame-Options", "DENY")
        response.headers.setdefault("Referrer-Policy", "strict-origin-when-cross-origin")
        response.headers.setdefault(
            "Permissions-Policy",
            "camera=(), microphone=(), geolocation=()",
        )
        if settings.app_env.lower() == "production" and request.url.scheme == "https":
            response.headers.setdefault(
                "Strict-Transport-Security",
                "max-age=31536000; includeSubDomains",
            )
        return response


app.add_middleware(SecurityHeadersMiddleware)
app.add_middleware(RequestIDMiddleware)
app.add_middleware(AccessLogMiddleware)
app.add_middleware(FixedWindowRateLimitMiddleware)

app.include_router(health_router)
app.include_router(agent_router)
app.include_router(appointments_router)
app.include_router(audit_router)
app.include_router(clinical_router)
app.include_router(consultations_router)
app.include_router(documents_router)
app.include_router(records_router)
app.include_router(provider_records_router)
app.include_router(research_router)
