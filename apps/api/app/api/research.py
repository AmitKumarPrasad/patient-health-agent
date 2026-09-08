from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field

from app.agents.research_agent import invoke_research_agent
from app.auth.keycloak import require_roles

router = APIRouter(prefix="/api/research", tags=["research"])


class ResearchRequest(BaseModel):
    message: str = Field(min_length=3, max_length=2000)


class ResearchResponse(BaseModel):
    response: str


@router.post("", response_model=ResearchResponse)
def research(
    request: ResearchRequest,
    _: dict = Depends(require_roles("patient", "provider", "admin")),
) -> ResearchResponse:
    try:
        return ResearchResponse(response=invoke_research_agent(request.message.strip()))
    except (RuntimeError, ValueError) as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc
