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


def test_only_owner_can_rename_research_session(db_session):
    session = ResearchSession(owner_subject="patient-a", title="Old title")
    db_session.add(session)
    db_session.commit()
    db_session.refresh(session)

    other = TestClient(_build_app(
        db_session, {"sub": "patient-b", "realm_access": {"roles": ["patient"]}}
    ))
    owner = TestClient(_build_app(
        db_session, {"sub": "patient-a", "realm_access": {"roles": ["patient"]}}
    ))
    url = f"/api/research/sessions/{session.id}"
    assert other.patch(url, json={"title": "Intrusion"}).status_code == 404
    assert owner.patch(url, json={"title": "   "}).status_code == 422
    assert owner.patch(url, json={"title": "x" * 201}).status_code == 422

    renamed = owner.patch(url, json={"title": "  New title  "})
    assert renamed.status_code == 200
    assert renamed.json()["title"] == "New title"
    assert owner.get(url).json()["title"] == "New title"


def test_research_history_search_is_case_insensitive_and_owner_scoped(db_session):
    db_session.add_all([
        ResearchSession(owner_subject="patient-a", title="Cardiac screening"),
        ResearchSession(owner_subject="patient-a", title="Nutrition basics"),
        ResearchSession(owner_subject="patient-b", title="Cardiac private notes"),
    ])
    db_session.commit()
    client = TestClient(_build_app(
        db_session, {"sub": "patient-a", "realm_access": {"roles": ["patient"]}}
    ))
    result = client.get("/api/research/sessions", params={"q": "CARDIAC"})
    assert result.status_code == 200
    assert [item["title"] for item in result.json()] == ["Cardiac screening"]
    assert client.get("/api/research/sessions", params={"q": "x" * 101}).status_code == 422
    assert client.get("/api/research/sessions", params={"q": "%"}).json() == []


def test_research_history_pagination_is_stable_and_owner_scoped(db_session):
    db_session.add_all([
        ResearchSession(owner_subject="patient-a", title=f"Page {i:02d}")
        for i in range(25)
    ] + [
        ResearchSession(owner_subject="patient-b", title="Other user's history")
    ])
    db_session.commit()
    client = TestClient(_build_app(
        db_session, {"sub": "patient-a", "realm_access": {"roles": ["patient"]}}
    ))
    first = client.get("/api/research/sessions", params={"limit": 10, "offset": 0})
    second = client.get("/api/research/sessions", params={"limit": 10, "offset": 10})
    third = client.get("/api/research/sessions", params={"limit": 10, "offset": 20})
    assert first.status_code == 200
    assert len(first.json()) == 10
    assert len(second.json()) == 10
    assert len(third.json()) == 5
    all_ids = [entry["id"] for result in (first, second, third) for entry in result.json()]
    assert len(set(all_ids)) == 25
    assert all(entry["title"].startswith("Page ") for result in (first, second, third) for entry in result.json())
    for params in ({"limit": 0}, {"limit": 51}, {"offset": -1}, {"offset": 100001}):
        assert client.get("/api/research/sessions", params=params).status_code == 422
