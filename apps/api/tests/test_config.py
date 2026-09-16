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


def _production_settings(**overrides):
    values = {
        "app_env": "production",
        "postgres_password": "strong-production-password",
        "minio_access_key": "production-access",
        "minio_secret_key": "strong-production-secret",
        "minio_secure": True,
        "keycloak_issuer_url": "https://identity.example.com/realms/patient-health",
        "keycloak_jwks_url": "https://identity.example.com/realms/patient-health/protocol/openid-connect/certs",
        "cors_origins": "https://app.example.com",
    }
    values.update(overrides)
    return Settings(**values)


def test_production_security_configuration_is_accepted() -> None:
    settings = _production_settings()

    assert settings.app_env == "production"
    assert settings.minio_secure is True


@pytest.mark.parametrize(
    ("field", "value"),
    [
        ("postgres_password", "patient_health"),
        ("minio_access_key", "minioadmin"),
        ("minio_secret_key", "minioadmin"),
        ("minio_secure", False),
        ("keycloak_issuer_url", "http://identity.example.com/realms/patient-health"),
        ("keycloak_jwks_url", "http://identity.example.com/realms/patient-health/protocol/openid-connect/certs"),
        ("cors_origins", "*"),
        ("cors_origins", ""),
        ("rate_limit_trust_forwarded_for", True),
    ],
)
def test_production_insecure_configuration_is_rejected(field: str, value) -> None:
    with pytest.raises(ValidationError):
        _production_settings(**{field: value})
