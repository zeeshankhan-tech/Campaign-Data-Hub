"""Ingestion trigger and status endpoints."""

from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, Body, Depends, status
from sqlalchemy.orm import Session

from app.api.schemas.ingestions import (
    IngestionCreateRequest,
    IngestionCreateResponse,
    IngestionStatusResponse,
)
from app.core.config import Settings, get_settings
from app.db.session import get_db
from app.services import ingestion_service

router = APIRouter(tags=["ingestions"])


@router.post(
    "/ingestions",
    response_model=IngestionCreateResponse,
    status_code=status.HTTP_201_CREATED,
)
def create_ingestion(
    body: IngestionCreateRequest = Body(default_factory=IngestionCreateRequest),
    db: Session = Depends(get_db),
    settings: Settings = Depends(get_settings),
) -> IngestionCreateResponse:
    """Trigger a full ingestion/re-ingestion run."""
    return ingestion_service.trigger_ingestion(db, settings, data_dir=body.data_dir)


@router.get("/ingestions/{ingestion_id}", response_model=IngestionStatusResponse)
def get_ingestion(
    ingestion_id: UUID, db: Session = Depends(get_db)
) -> IngestionStatusResponse:
    """Fetch ingestion run status and summary."""
    return ingestion_service.get_ingestion(db, ingestion_id)
