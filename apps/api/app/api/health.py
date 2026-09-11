from fastapi import APIRouter, Depends
from fastapi.responses import JSONResponse, Response
from sqlalchemy import text
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.observability import prometheus_response

router = APIRouter(tags=["health"])


@router.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


@router.get("/health/db")
def database_health(db: Session = Depends(get_db)) -> dict[str, str]:
    db.execute(text("SELECT 1"))
    return {"status": "ok", "database": "reachable"}


@router.get("/ready", response_model=None)
def readiness(db: Session = Depends(get_db)) -> dict[str, str] | JSONResponse:
    try:
        db.execute(text("SELECT 1"))
    except SQLAlchemyError:
        return JSONResponse(
            status_code=503,
            content={"status": "not_ready", "database": "unreachable"},
        )
    return {"status": "ready"}


@router.get("/metrics", include_in_schema=False)
def metrics() -> Response:
    payload, content_type = prometheus_response()
    return Response(content=payload, media_type=content_type.split(";", 1)[0])
