from __future__ import annotations

from uuid import uuid4

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import Session
from sqlalchemy.pool import StaticPool

from app.api.research import router
from app.auth.keycloak import get_current_user
from app.db.base import Base
from app.db.session import get_db
from app.models.research import ResearchMessage, ResearchSession


@pytest.fixture
def db_session():
    engine = create_engine(
        "sqlite+pysqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(engine, tables=[ResearchSession.__table__, ResearchMessage.__table__])
    with Session(engine) as db:
        yield db
    engine.dispose()


def _build_app(db, user):
    app = FastAPI()
    app.include_router(router)
    app.dependency_overrides[get_db] = lambda: db
    app.dependency_overrides[get_current_user] = lambda: user
    return app


def test_research_session_is_owner_scoped(db_session):
    owner = {"sub": "patient-a", "realm_access": {"roles": ["patient"]}}
    other = {"sub": "patient-b", "realm_access": {"roles": ["patient"]}}
    session = ResearchSession(owner_subject="patient-a", title="Private research")
    db_session.add(session)
    db_session.commit()
    db_session.refresh(session)

    owner_client = TestClient(_build_app(db_session, owner))
    other_client = TestClient(_build_app(db_session, other))

    assert owner_client.get(f"/api/research/sessions/{session.id}").status_code == 200
    assert other_client.get(f"/api/research/sessions/{session.id}").status_code == 404


def test_research_session_list_excludes_other_users(db_session):
    db_session.add_all(
        [
            ResearchSession(owner_subject="patient-a", title="A"),
            ResearchSession(owner_subject="patient-b", title="B"),
        ]
    )
    db_session.commit()

    client = TestClient(
        _build_app(
            db_session,
            {"sub": "patient-a", "realm_access": {"roles": ["patient"]}},
        )
    )

    response = client.get("/api/research/sessions")
    assert response.status_code == 200
    assert [item["title"] for item in response.json()] == ["A"]


def test_missing_research_session_returns_404(db_session):
    client = TestClient(
        _build_app(
            db_session,
            {"sub": "patient-a", "realm_access": {"roles": ["patient"]}},
        )
    )

    response = client.get(f"/api/research/sessions/{uuid4()}")
    assert response.status_code == 404
    assert response.json()["detail"] == "Research session not found"


def test_only_owner_can_delete_research_session(db_session):
    session = ResearchSession(owner_subject="patient-a", title="Delete this")
    db_session.add(session)
    db_session.commit()
    db_session.refresh(session)

    other = TestClient(_build_app(
        db_session, {"sub": "patient-b", "realm_access": {"roles": ["patient"]}}
    ))
    owner = TestClient(_build_app(
        db_session, {"sub": "patient-a", "realm_access": {"roles": ["patient"]}}
    ))

    assert other.delete(f"/api/research/sessions/{session.id}").status_code == 404
    assert db_session.get(ResearchSession, session.id) is not None
    assert owner.delete(f"/api/research/sessions/{session.id}").status_code == 204
    assert owner.get(f"/api/research/sessions/{session.id}").status_code == 404
