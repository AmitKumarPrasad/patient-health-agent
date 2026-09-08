from functools import lru_cache

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
    keycloak_jwks_cache_ttl_seconds: int = 300

    rate_limit_requests: int = 120
    rate_limit_window_seconds: int = 60

    smtp_host: str = "localhost"
    smtp_port: int = 1025
    smtp_from: str = "no-reply@patient-health.local"

    jitsi_base_url: str = "http://localhost:8443"

    minio_endpoint: str = "localhost:9000"
    minio_access_key: str = "minioadmin"
    minio_secret_key: str = "minioadmin"
    minio_bucket: str = "patient-records"
    minio_secure: bool = False

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
