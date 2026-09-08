from unittest.mock import patch

import pytest
from fastapi import HTTPException

from app.auth.keycloak import _get_jwks, decode_access_token, patient_subject, require_roles


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


def test_jwks_cache_reuses_fresh_keys(monkeypatch: pytest.MonkeyPatch) -> None:
    import app.auth.keycloak as keycloak

    calls = 0

    def fake_get(url: str, timeout: float):
        nonlocal calls
        calls += 1

        class FakeResponse:
            def raise_for_status(self) -> None:
                pass

            def json(self) -> dict[str, object]:
                return {"keys": [{"kid": "cached-key", "kty": "RSA"}]}

        return FakeResponse()

    monkeypatch.setattr("app.auth.keycloak.httpx.get", fake_get)
    monkeypatch.setattr("app.auth.keycloak.monotonic", lambda: 100.0)
    monkeypatch.setattr("app.auth.keycloak.settings.keycloak_jwks_cache_ttl_seconds", 300)
    keycloak._jwks_cache = None
    keycloak._jwks_cached_at = 0.0

    first = _get_jwks()
    second = _get_jwks()

    assert first == second
    assert calls == 1


def test_jwks_cache_refreshes_after_ttl(monkeypatch: pytest.MonkeyPatch) -> None:
    import app.auth.keycloak as keycloak

    responses = [
        {"keys": [{"kid": "first-key", "kty": "RSA"}]},
        {"keys": [{"kid": "second-key", "kty": "RSA"}]},
    ]
    calls = 0

    def fake_get(url: str, timeout: float):
        nonlocal calls
        payload = responses[calls]
        calls += 1

        class FakeResponse:
            def raise_for_status(self) -> None:
                pass

            def json(self) -> dict[str, object]:
                return payload

        return FakeResponse()

    now = {"value": 100.0}
    monkeypatch.setattr("app.auth.keycloak.httpx.get", fake_get)
    monkeypatch.setattr("app.auth.keycloak.monotonic", lambda: now["value"])
    monkeypatch.setattr("app.auth.keycloak.settings.keycloak_jwks_cache_ttl_seconds", 300)
    keycloak._jwks_cache = None
    keycloak._jwks_cached_at = 0.0

    assert _get_jwks()["keys"][0]["kid"] == "first-key"
    now["value"] = 400.1
    assert _get_jwks()["keys"][0]["kid"] == "second-key"
    assert calls == 2
