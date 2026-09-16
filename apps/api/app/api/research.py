from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field

from app.agents.research_agent import invoke_research_agent
from app.auth.keycloak import require_roles

router = APIRouter(prefix="/api/research", tags=["research"])


class ResearchRequest(BaseModel):
    message: str = Field(min_length=3, max_length=2000)


class ResearchSource(BaseModel):
    title: str
    url: str


class ResearchResponse(BaseModel):
    response: str
    sources: list[ResearchSource]


@router.post("", response_model=ResearchResponse)
def research(
    request: ResearchRequest,
    _: dict = Depends(require_roles("patient", "provider", "admin")),
) -> ResearchResponse:
    try:
        result = invoke_research_agent(request.message.strip())
        return ResearchResponse(**result)
    except (RuntimeError, ValueError) as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc
