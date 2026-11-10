"""Ingestion trigger/status application service."""

from __future__ import annotations

from pathlib import Path
from uuid import UUID

from sqlalchemy.orm import Session

from app.api.schemas.ingestions import IngestionCreateResponse, IngestionStatusResponse
from app.core.config import Settings
from app.core.exceptions import NotFoundError, ValidationAppError
from app.db.models import IngestionRun
from app.ingestion.pipeline import run_ingestion


def trigger_ingestion(
    session: Session,
    settings: Settings,
    *,
    data_dir: str | None = None,
) -> IngestionCreateResponse:
    if data_dir:
        path = Path(data_dir).expanduser().resolve()
    else:
        path = (Path.cwd() / settings.assessment_data_dir).resolve()

    if not path.exists() or not path.is_dir():
        raise ValidationAppError(f"data_dir does not exist or is not a directory: {path}")
    if not (path / "deliveries").is_dir():
        raise ValidationAppError(f"data_dir missing deliveries/: {path}")
    if not (path / "exchange_rates.json").is_file():
        raise ValidationAppError(f"data_dir missing exchange_rates.json: {path}")

    result = run_ingestion(session, data_dir=path)
    return IngestionCreateResponse(
        id=UUID(result.run_id),
        status=result.status,
        accepted_total=result.accepted_total,
        rejected_total=result.rejected_total,
        summary=result.summary,
    )


def get_ingestion(session: Session, ingestion_id: UUID) -> IngestionStatusResponse:
    run = session.get(IngestionRun, ingestion_id)
    if run is None:
        raise NotFoundError(f"Ingestion run {ingestion_id} not found")
    return IngestionStatusResponse.model_validate(run)
