from functools import lru_cache
from urllib.parse import urlsplit

from pydantic import Field, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    app_env: str = "development"
    app_name: str = "patient-health-agent"
    cors_origins: str = "http://localhost:3000"

    postgres_host: str = "localhost"
    postgres_port: int = 5432
    postgres_db: str = "patient_health"
    postgres_user: str = "patient_health"
    postgres_password: str = "patient_health"

    openai_api_key: str | None = None
    openai_model: str = "gpt-5.6-luna"
    openai_embedding_model: str = "text-embedding-3-small"
    tavily_api_key: str | None = None

    keycloak_issuer_url: str = "http://localhost:8080/realms/patient-health"
    keycloak_jwks_url: str = "http://keycloak:8080/realms/patient-health/protocol/openid-connect/certs"
    keycloak_audience: str | None = None
    keycloak_jwks_cache_ttl_seconds: int = Field(default=300, gt=0)

    rate_limit_requests: int = Field(default=120, ge=0)
    rate_limit_window_seconds: int = Field(default=60, gt=0)
    rate_limit_trust_forwarded_for: bool = False
    max_request_body_bytes: int = Field(default=12 * 1024 * 1024, gt=0)

    smtp_host: str = "localhost"
    smtp_port: int = 1025
    smtp_from: str = "no-reply@patient-health.local"

    jitsi_base_url: str = "http://localhost:8443"

    minio_endpoint: str = "localhost:9000"
    minio_access_key: str = "minioadmin"
    minio_secret_key: str = "minioadmin"
    minio_bucket: str = "patient-records"
    minio_secure: bool = False

    antivirus_enabled: bool = False
    antivirus_host: str = "localhost"
    antivirus_port: int = Field(default=3310, ge=1, le=65535)
    antivirus_timeout_seconds: float = Field(default=15.0, gt=0)

    @model_validator(mode="after")
    def validate_production_security(self):
        if self.app_env.lower() not in {"production", "prod"}:
            return self

        errors: list[str] = []
        if self.postgres_password == "patient_health":
            errors.append("POSTGRES_PASSWORD must not use the development default in production")
        if self.minio_access_key == "minioadmin" or self.minio_secret_key == "minioadmin":
            errors.append("MINIO credentials must not use the development defaults in production")
        if not self.minio_secure:
            errors.append("MINIO_SECURE must be true in production")
        if not self.keycloak_issuer_url.lower().startswith("https://"):
            errors.append("KEYCLOAK_ISSUER_URL must use HTTPS in production")
        if not self.keycloak_jwks_url.lower().startswith("https://"):
            errors.append("KEYCLOAK_JWKS_URL must use HTTPS in production")
        origins = [origin.strip() for origin in self.cors_origins.split(",") if origin.strip()]
        if not origins or "*" in origins:
            errors.append("CORS_ORIGINS must contain explicit origins in production")
        for origin in origins:
            try:
                parsed = urlsplit(origin)
                hostname = (parsed.hostname or "").lower().rstrip(".")
                if (
                    parsed.scheme != "https"
                    or not hostname
                    or hostname == "localhost"
                    or hostname.endswith((".localhost", ".local", ".internal"))
                    or parsed.username is not None
                    or parsed.password is not None
                    or parsed.path not in ("", "/")
                    or parsed.query
                    or parsed.fragment
                    or parsed.port == 0
                    or "*" in hostname
                ):
                    errors.append("CORS_ORIGINS must use explicit HTTPS web origins in production")
            except ValueError:
                errors.append("CORS_ORIGINS contains an invalid web origin")
        if self.rate_limit_requests <= 0:
            errors.append("RATE_LIMIT_REQUESTS must be greater than zero in production")
        if self.rate_limit_trust_forwarded_for:
            errors.append("RATE_LIMIT_TRUST_FORWARDED_FOR must remain false unless the trusted proxy is explicitly configured")
        if errors:
            raise ValueError("Production security validation failed: " + "; ".join(errors))
        return self

    @property
    def database_url(self) -> str:
        return (
            f"postgresql+psycopg://{self.postgres_user}:{self.postgres_password}"
            f"@{self.postgres_host}:{self.postgres_port}/{self.postgres_db}"
        )

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )


@lru_cache
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
