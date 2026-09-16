from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from app.agents.research_agent import invoke_research_agent
from app.auth.keycloak import patient_subject, require_roles
from app.db.session import get_db
from app.models.research import ResearchMessage, ResearchSession

router = APIRouter(prefix="/api/research", tags=["research"])


class ResearchRequest(BaseModel):
    message: str = Field(min_length=3, max_length=2000)


class ResearchSource(BaseModel):
    title: str
    url: str


class ResearchResponse(BaseModel):
    response: str
    sources: list[ResearchSource]


class ResearchSessionSummary(BaseModel):
    id: UUID
    title: str
    created_at: str
    updated_at: str


class ResearchMessageResponse(BaseModel):
    id: UUID
    role: str
    content: str
    sources: list[ResearchSource] = []
    created_at: str


class ResearchSessionResponse(BaseModel):
    id: UUID
    title: str
    created_at: str
    updated_at: str
    messages: list[ResearchMessageResponse]


def _session_response(session: ResearchSession) -> ResearchSessionResponse:
    return ResearchSessionResponse(
        id=session.id,
        title=session.title,
        created_at=session.created_at.isoformat(),
        updated_at=session.updated_at.isoformat(),
        messages=[
            ResearchMessageResponse(
                id=message.id,
                role=message.role,
                content=message.content,
                sources=[ResearchSource(**source) for source in (message.sources or [])],
                created_at=message.created_at.isoformat(),
            )
            for message in session.messages
        ],
    )


def _owned_session(db: Session, session_id: UUID, owner_subject: str) -> ResearchSession:
    session = db.scalar(
        select(ResearchSession)
        .options(selectinload(ResearchSession.messages))
        .where(ResearchSession.id == session_id, ResearchSession.owner_subject == owner_subject)
    )
    if session is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Research session not found")
    return session


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


@router.post("/sessions", response_model=ResearchSessionResponse, status_code=status.HTTP_201_CREATED)
def create_session(
    _: dict = Depends(require_roles("patient", "provider", "admin")),
    db: Session = Depends(get_db),
) -> ResearchSessionResponse:
    user = _
    session = ResearchSession(owner_subject=patient_subject(user), title="New research session")
    db.add(session)
    db.commit()
    db.refresh(session)
    session.messages = []
    return _session_response(session)


@router.get("/sessions", response_model=list[ResearchSessionSummary])
def list_sessions(
    _: dict = Depends(require_roles("patient", "provider", "admin")),
    db: Session = Depends(get_db),
) -> list[ResearchSessionSummary]:
    rows = db.scalars(
        select(ResearchSession)
        .where(ResearchSession.owner_subject == patient_subject(_))
        .order_by(ResearchSession.updated_at.desc())
        .limit(50)
    ).all()
    return [
        ResearchSessionSummary(
            id=row.id,
            title=row.title,
            created_at=row.created_at.isoformat(),
            updated_at=row.updated_at.isoformat(),
        )
        for row in rows
    ]


@router.get("/sessions/{session_id}", response_model=ResearchSessionResponse)
def get_session(
    session_id: UUID,
    _: dict = Depends(require_roles("patient", "provider", "admin")),
    db: Session = Depends(get_db),
) -> ResearchSessionResponse:
    return _session_response(_owned_session(db, session_id, patient_subject(_)))


@router.post("/sessions/{session_id}/messages", response_model=ResearchSessionResponse)
def send_session_message(
    session_id: UUID,
    request: ResearchRequest,
    _: dict = Depends(require_roles("patient", "provider", "admin")),
    db: Session = Depends(get_db),
) -> ResearchSessionResponse:
    session = _owned_session(db, session_id, patient_subject(_))
    question = request.message.strip()
    if not question:
        raise HTTPException(status_code=422, detail="Research message cannot be blank")

    history = [{"role": message.role, "content": message.content} for message in session.messages]
    user_message = ResearchMessage(session=session, role="user", content=question)
    db.add(user_message)
    try:
        result = invoke_research_agent(question, history=history)
    except (RuntimeError, ValueError) as exc:
        db.rollback()
        raise HTTPException(status_code=503, detail=str(exc)) from exc

    db.add(
        ResearchMessage(
            session=session,
            role="assistant",
            content=result["response"],
            sources=result["sources"],
        )
    )
    if session.title == "New research session":
        session.title = question[:80]
    db.commit()
    db.refresh(session)
    session = _owned_session(db, session_id, patient_subject(_))
    return _session_response(session)
