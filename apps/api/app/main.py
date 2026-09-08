from fastapi import FastAPI

from app.api.agent import router as agent_router
from app.api.appointments import router as appointments_router
from app.api.clinical import router as clinical_router
from app.api.consultations import router as consultations_router
from app.api.documents import router as documents_router
from app.api.health import router as health_router
from app.api.provider_records import router as provider_records_router
from app.api.records import router as records_router
from app.config import settings

app = FastAPI(
    title=settings.app_name,
    version="0.1.0",
    description="Backend API for the Patient Health Agent platform.",
)

app.include_router(health_router)
app.include_router(agent_router)
app.include_router(appointments_router)
app.include_router(clinical_router)
app.include_router(consultations_router)
app.include_router(documents_router)
app.include_router(records_router)
app.include_router(provider_records_router)
