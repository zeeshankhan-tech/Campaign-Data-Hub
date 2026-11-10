"""Health and readiness endpoints."""

from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlalchemy import text
from sqlalchemy.orm import Session

from app.core.config import Settings, get_settings
from app.db.session import get_db

router = APIRouter(tags=["health"])


class HealthResponse(BaseModel):
    """Process and dependency health snapshot."""

    status: str
    app: str
    environment: str
    database: str


@router.get("/health", response_model=HealthResponse)
def get_health(
    settings: Settings = Depends(get_settings),
    db: Session = Depends(get_db),
) -> HealthResponse:
    """
    Report API liveness and database connectivity.

    Returns HTTP 200 when the process is up. Database connectivity is reflected
    in the `database` field (`ok` or `unavailable`) so operators can distinguish
    process-up from dependency-up without failing local bring-up mid-debug.
    """
    database_status = "ok"
    try:
        db.execute(text("SELECT 1"))
    except Exception:
        database_status = "unavailable"

    overall = "ok" if database_status == "ok" else "degraded"
    return HealthResponse(
        status=overall,
        app=settings.app_name,
        environment=settings.app_env,
        database=database_status,
    )
