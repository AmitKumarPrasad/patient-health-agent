from fastapi import FastAPI

from app.api.agent import router as agent_router
from app.api.appointments import router as appointments_router
from app.api.health import router as health_router
from app.config import settings

app = FastAPI(
    title=settings.app_name,
    version="0.1.0",
    description="Backend API for the Patient Health Agent platform.",
)

app.include_router(health_router)
app.include_router(agent_router)
app.include_router(appointments_router)
