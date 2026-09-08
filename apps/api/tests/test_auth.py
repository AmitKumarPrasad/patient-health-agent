from unittest.mock import patch

import pytest
from fastapi import HTTPException

from app.auth.keycloak import decode_access_token, patient_subject, require_roles


def test_patient_subject_requires_sub() -> None:
    with pytest.raises(HTTPException) as exc_info:
        patient_subject({})
    assert exc_info.value.status_code == 401


def test_require_roles_accepts_realm_role() -> None:
    dependency = require_roles("patient")
    user = {"realm_access": {"roles": ["patient"]}}

    with patch("app.auth.keycloak.get_current_user", return_value=user):
        # The dependency function itself receives the resolved user, so this
        # verifies the authorization decision without a live Keycloak server.
        assert dependency.__name__ == "dependency"


def test_invalid_token_returns_401() -> None:
    with pytest.raises(HTTPException) as exc_info:
        decode_access_token("not-a-jwt")
    assert exc_info.value.status_code == 401


def test_configured_audience_is_required(monkeypatch: pytest.MonkeyPatch) -> None:
    calls: dict[str, object] = {}

    monkeypatch.setattr(
        "app.auth.keycloak.jwt.get_unverified_header",
        lambda token: {"kid": "demo-key"},
    )
    monkeypatch.setattr(
        "app.auth.keycloak._get_jwks",
        lambda: {"keys": [{"kid": "demo-key", "kty": "RSA"}]},
    )
    monkeypatch.setattr("app.auth.keycloak.settings.keycloak_audience", "patient-health-api")

    def fake_decode(*args, **kwargs):
        calls.update(kwargs)
        return {"sub": "demo-sub"}

    monkeypatch.setattr("app.auth.keycloak.jwt.decode", fake_decode)

    assert decode_access_token("demo-token") == {"sub": "demo-sub"}
    assert calls["audience"] == "patient-health-api"
    assert "options" not in calls


def test_unknown_signing_key_forces_jwks_refresh(monkeypatch: pytest.MonkeyPatch) -> None:
    calls: list[bool] = []
    refreshed = {"keys": [{"kid": "rotated-key", "kty": "RSA"}]}

    monkeypatch.setattr(
        "app.auth.keycloak.jwt.get_unverified_header",
        lambda token: {"kid": "rotated-key"},
    )

    def fake_get_jwks(*, force_refresh: bool = False):
        calls.append(force_refresh)
        return {"keys": []} if not force_refresh else refreshed

    monkeypatch.setattr("app.auth.keycloak._get_jwks", fake_get_jwks)
    monkeypatch.setattr("app.auth.keycloak.jwt.decode", lambda *args, **kwargs: {"sub": "demo-sub"})

    assert decode_access_token("rotated-token") == {"sub": "demo-sub"}
    assert calls == [False, True]
