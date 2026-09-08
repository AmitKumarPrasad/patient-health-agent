from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field

from app.agents.appointment_agent import invoke_appointment_agent
from app.auth.keycloak import get_current_user, patient_subject

router = APIRouter(prefix="/api/agent", tags=["agent"])


class AgentRequest(BaseModel):
    message: str = Field(min_length=1, max_length=4000)


class AgentResponse(BaseModel):
    response: str


@router.post("/chat", response_model=AgentResponse)
def chat(
    request: AgentRequest,
    user: dict = Depends(get_current_user),
) -> AgentResponse:
    subject = patient_subject(user)
    try:
        response = invoke_appointment_agent(request.message, subject)
    except LookupError as exc:
        raise HTTPException(status_code=403, detail=str(exc)) from exc
    except (RuntimeError, ValueError) as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc
    return AgentResponse(response=response)
