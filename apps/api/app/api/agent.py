from fastapi import APIRouter, Depends, HTTPException, Request
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
    payload: AgentRequest,
    request: Request,
    user: dict = Depends(get_current_user),
) -> AgentResponse:
    subject = patient_subject(user)
    request_id = getattr(request.state, "request_id", None)
    try:
        response = invoke_appointment_agent(payload.message, subject, request_id)
    except LookupError as exc:
        raise HTTPException(status_code=403, detail=str(exc)) from exc
    except (RuntimeError, ValueError) as exc:
        raise HTTPException(status_code=503, detail="AI assistant is temporarily unavailable") from exc
    return AgentResponse(response=response)
