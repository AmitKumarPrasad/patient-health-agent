import pytest
from pydantic import ValidationError

from app.config import Settings


def test_default_security_timing_configuration_is_valid() -> None:
    settings = Settings()

    assert settings.keycloak_jwks_cache_ttl_seconds == 300
    assert settings.rate_limit_requests == 120
    assert settings.rate_limit_window_seconds == 60


@pytest.mark.parametrize(
    ("field", "value"),
    [
        ("keycloak_jwks_cache_ttl_seconds", 0),
        ("rate_limit_window_seconds", 0),
        ("rate_limit_requests", -1),
    ],
)
def test_invalid_security_timing_configuration_is_rejected(field: str, value: int) -> None:
    with pytest.raises(ValidationError):
        Settings(**{field: value})


def test_rate_limiting_can_be_disabled_with_zero_request_limit() -> None:
    settings = Settings(rate_limit_requests=0)

    assert settings.rate_limit_requests == 0
