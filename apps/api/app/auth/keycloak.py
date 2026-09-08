from __future__ import annotations

from time import monotonic
from typing import Any

import httpx
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from jose import JWTError, jwt

from app.config import settings


bearer_scheme = HTTPBearer(auto_error=False)

_jwks_cache: dict[str, Any] | None = None
_jwks_cached_at = 0.0


def _get_jwks(*, force_refresh: bool = False) -> dict[str, Any]:
    global _jwks_cache, _jwks_cached_at
    now = monotonic()
    if (
        not force_refresh
        and _jwks_cache is not None
        and now - _jwks_cached_at < settings.keycloak_jwks_cache_ttl_seconds
    ):
        return _jwks_cache

    try:
        response = httpx.get(settings.keycloak_jwks_url, timeout=5.0)
        response.raise_for_status()
        jwks = response.json()
    except (httpx.HTTPError, ValueError) as exc:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Authentication provider is unavailable",
        ) from exc

    if not isinstance(jwks, dict) or not isinstance(jwks.get("keys"), list):
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Authentication provider returned invalid signing keys",
        )

    _jwks_cache = jwks
    _jwks_cached_at = now
    return jwks


def decode_access_token(token: str) -> dict[str, Any]:
    try:
        header = jwt.get_unverified_header(token)
        kid = header.get("kid")
        if not kid:
            raise JWTError("Token has no key id")

        jwks = _get_jwks()
        key = next((item for item in jwks.get("keys", []) if item.get("kid") == kid), None)
        if key is None:
            jwks = _get_jwks(force_refresh=True)
            key = next((item for item in jwks.get("keys", []) if item.get("kid") == kid), None)
        if key is None:
            raise JWTError("Signing key not found")

        if settings.keycloak_audience is None:
            options = {"verify_aud": False}
            return jwt.decode(
                token,
                key,
                algorithms=["RS256"],
                issuer=settings.keycloak_issuer_url,
                options=options,
            )

        return jwt.decode(
            token,
            key,
            algorithms=["RS256"],
            issuer=settings.keycloak_issuer_url,
            audience=settings.keycloak_audience,
        )
    except (JWTError, ValueError, TypeError) as exc:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid access token",
            headers={"WWW-Authenticate": "Bearer"},
        ) from exc


def get_current_user(
    credentials: HTTPAuthorizationCredentials | None = Depends(bearer_scheme),
) -> dict[str, Any]:
    if credentials is None or credentials.scheme.lower() != "bearer":
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Bearer access token required",
            headers={"WWW-Authenticate": "Bearer"},
        )
    return decode_access_token(credentials.credentials)


def require_roles(*roles: str):
    def dependency(user: dict[str, Any] = Depends(get_current_user)) -> dict[str, Any]:
        realm_roles = set(user.get("realm_access", {}).get("roles", []))
        client_roles: set[str] = set()
        for client in user.get("resource_access", {}).values():
            client_roles.update(client.get("roles", []))

        if not realm_roles.intersection(roles) and not client_roles.intersection(roles):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Insufficient role",
            )
        return user

    return dependency


def patient_subject(user: dict[str, Any]) -> str:
    subject = user.get("sub")
    if not subject:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token subject is required",
        )
    return str(subject)
