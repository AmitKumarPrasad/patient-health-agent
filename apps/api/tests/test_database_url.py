from sqlalchemy.engine import make_url

from app.config import Settings


def test_database_url_round_trips_reserved_credential_characters() -> None:
    settings = Settings(
        postgres_user="patient@service",
        postgres_password="p@ss:word/part?#%",
    )

    parsed = make_url(settings.database_url)

    assert parsed.username == "patient@service"
    assert parsed.password == "p@ss:word/part?#%"
    assert parsed.host == "localhost"
    assert parsed.port == 5432
    assert parsed.database == "patient_health"


def test_database_url_preserves_default_connection_string() -> None:
    settings = Settings()

    assert settings.database_url == (
        "postgresql+psycopg://patient_health:patient_health@localhost:5432/patient_health"
    )
