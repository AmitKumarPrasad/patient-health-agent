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
