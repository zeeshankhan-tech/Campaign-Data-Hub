"""Delivery health and quality-report endpoints."""

from __future__ import annotations

from typing import Optional
from uuid import UUID

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.api.schemas.deliveries import DeliveryItem, DeliveryListResponse, QualityReportResponse
from app.db.session import get_db
from app.services import deliveries_service

router = APIRouter(tags=["deliveries"])


@router.get("/deliveries", response_model=DeliveryListResponse)
def list_deliveries(
    platform: Optional[str] = Query(default=None),
    health: Optional[str] = Query(default=None),
    limit: int = Query(default=100, ge=1, le=500),
    offset: int = Query(default=0, ge=0),
    db: Session = Depends(get_db),
) -> DeliveryListResponse:
    """List deliveries with health classification."""
    return deliveries_service.list_deliveries(
        db, platform=platform, health=health, limit=limit, offset=offset
    )


@router.get("/deliveries/{delivery_id}", response_model=DeliveryItem)
def get_delivery(delivery_id: UUID, db: Session = Depends(get_db)) -> DeliveryItem:
    """Get one delivery by id."""
    return deliveries_service.get_delivery(db, delivery_id)


@router.get(
    "/deliveries/{delivery_id}/quality-report",
    response_model=QualityReportResponse,
)
def get_quality_report(
    delivery_id: UUID, db: Session = Depends(get_db)
) -> QualityReportResponse:
    """Return structured quality-check findings for a delivery."""
    return deliveries_service.get_quality_report(db, delivery_id)
