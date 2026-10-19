from collections.abc import Generator

from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

from app.config import settings


def create_database_engine(database_url: str, connect_timeout_seconds: int):
    return create_engine(
        database_url,
        connect_args={"connect_timeout": connect_timeout_seconds},
        pool_pre_ping=True,
    )


engine = create_database_engine(settings.database_url, settings.postgres_connect_timeout_seconds)
SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False)


def get_db() -> Generator[Session, None, None]:
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
