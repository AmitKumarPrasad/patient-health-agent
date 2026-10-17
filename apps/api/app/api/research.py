from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field, field_validator
from sqlalchemy import func, select
from sqlalchemy.orm import Session, selectinload

from app.agents.research_agent import invoke_research_agent
from app.auth.keycloak import patient_subject, require_roles
from app.db.session import get_db
from app.models.research import ResearchMessage, ResearchSession

router = APIRouter(prefix="/api/research", tags=["research"])


class ResearchRequest(BaseModel):
    message: str = Field(min_length=3, max_length=2000)

    @field_validator("message")
    @classmethod
    def validate_message(cls, value: str) -> str:
        value = value.strip()
        if len(value) < 3:
            raise ValueError("Research message must contain at least 3 non-whitespace characters")
        return value


class ResearchTitleUpdate(BaseModel):
    title: str = Field(min_length=1, max_length=200)

    @field_validator("title")
    @classmethod
    def validate_title(cls, value: str) -> str:
        title = value.strip()
        if not title:
            raise ValueError("Research title cannot be blank")
        return title


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
    sources: list[ResearchSource] = Field(default_factory=list)
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


def _owned_session(
    db: Session, session_id: UUID, owner_subject: str
) -> ResearchSession:
    session = db.scalar(
        select(ResearchSession)
        .options(selectinload(ResearchSession.messages))
        .where(
            ResearchSession.id == session_id,
            ResearchSession.owner_subject == owner_subject,
        )
    )
    if session is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Research session not found",
        )
    return session


@router.post("", response_model=ResearchResponse)
def research(
    request: ResearchRequest,
    _: dict = Depends(require_roles("patient", "provider", "admin")),
) -> ResearchResponse:
    try:
        return ResearchResponse(**invoke_research_agent(request.message))
    except (RuntimeError, ValueError) as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc


@router.post(
    "/sessions",
    response_model=ResearchSessionResponse,
    status_code=status.HTTP_201_CREATED,
)
def create_session(
    user: dict = Depends(require_roles("patient", "provider", "admin")),
    db: Session = Depends(get_db),
) -> ResearchSessionResponse:
    session = ResearchSession(
        owner_subject=patient_subject(user),
        title="New research session",
    )
    db.add(session)
    db.commit()
    db.refresh(session)
    session.messages = []
    return _session_response(session)


@router.get("/sessions", response_model=list[ResearchSessionSummary])
def list_sessions(
    user: dict = Depends(require_roles("patient", "provider", "admin")),
    db: Session = Depends(get_db),
) -> list[ResearchSessionSummary]:
    rows = db.scalars(
        select(ResearchSession)
        .where(ResearchSession.owner_subject == patient_subject(user))
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
    user: dict = Depends(require_roles("patient", "provider", "admin")),
    db: Session = Depends(get_db),
) -> ResearchSessionResponse:
    return _session_response(_owned_session(db, session_id, patient_subject(user)))


@router.post(
    "/sessions/{session_id}/messages",
    response_model=ResearchSessionResponse,
)
def send_session_message(
    session_id: UUID,
    request: ResearchRequest,
    user: dict = Depends(require_roles("patient", "provider", "admin")),
    db: Session = Depends(get_db),
) -> ResearchSessionResponse:
    owner = patient_subject(user)
    session = _owned_session(db, session_id, owner)
    question = request.message
    history = [
        {"role": message.role, "content": message.content}
        for message in session.messages
    ]

    try:
        result = invoke_research_agent(question, history=history)
    except (RuntimeError, ValueError) as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc

    db.add(ResearchMessage(session=session, role="user", content=question))
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
    session.updated_at = func.now()
    db.commit()

    return _session_response(_owned_session(db, session_id, owner))


@router.delete("/sessions/{session_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_session(
    session_id: UUID,
    user: dict = Depends(require_roles("patient", "provider", "admin")),
    db: Session = Depends(get_db),
) -> None:
    session = _owned_session(db, session_id, patient_subject(user))
    db.delete(session)
    db.commit()


@router.patch("/sessions/{session_id}", response_model=ResearchSessionResponse)
def rename_session(
    session_id: UUID,
    request: ResearchTitleUpdate,
    user: dict = Depends(require_roles("patient", "provider", "admin")),
    db: Session = Depends(get_db),
) -> ResearchSessionResponse:
    owner = patient_subject(user)
    session = _owned_session(db, session_id, owner)
    session.title = request.title
    session.updated_at = func.now()
    db.commit()
    return _session_response(_owned_session(db, session_id, owner))
