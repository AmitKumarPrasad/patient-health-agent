from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
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


class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next) -> Response:
        response = await call_next(request)
        response.headers.setdefault("X-Content-Type-Options", "nosniff")
        response.headers.setdefault("X-Frame-Options", "DENY")
        response.headers.setdefault("Referrer-Policy", "strict-origin-when-cross-origin")
        return response


app.add_middleware(SecurityHeadersMiddleware)

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
