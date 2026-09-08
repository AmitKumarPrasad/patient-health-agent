from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from app.agents.appointment_agent import build_appointment_graph

router = APIRouter(prefix="/api/agent", tags=["agent"])


class AgentRequest(BaseModel):
    message: str = Field(min_length=1, max_length=4000)


class AgentResponse(BaseModel):
    response: str


@router.post("/chat", response_model=AgentResponse)
def chat(request: AgentRequest) -> AgentResponse:
    try:
        result = build_appointment_graph().invoke({"user_request": request.message})
    except RuntimeError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc
    return AgentResponse(response=result["response"])
