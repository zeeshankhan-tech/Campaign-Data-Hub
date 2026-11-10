"""Deliveries / data-health application service."""

from __future__ import annotations

from typing import Optional
from uuid import UUID

from sqlalchemy.orm import Session

from app.api.schemas.common import PaginationMeta
from app.api.schemas.deliveries import (
    DeliveryItem,
    DeliveryListResponse,
    QualityFindingItem,
    QualityReportResponse,
)
from app.core.exceptions import ValidationAppError
from app.repositories import deliveries as deliveries_repo


def list_deliveries(
    session: Session,
    *,
    platform: Optional[str] = None,
    health: Optional[str] = None,
    limit: int = 100,
    offset: int = 0,
) -> DeliveryListResponse:
    if limit < 1 or limit > 500:
        raise ValidationAppError("limit must be between 1 and 500")
    if offset < 0:
        raise ValidationAppError("offset must be >= 0")

    rows, total = deliveries_repo.list_deliveries(
        session, platform=platform, health=health, limit=limit, offset=offset
    )
    return DeliveryListResponse(
        items=[DeliveryItem.model_validate(row) for row in rows],
        pagination=PaginationMeta(limit=limit, offset=offset, total=total),
    )


def get_delivery(session: Session, delivery_id: UUID) -> DeliveryItem:
    delivery = deliveries_repo.get_delivery(session, delivery_id)
    return DeliveryItem.model_validate(delivery)


def get_quality_report(session: Session, delivery_id: UUID) -> QualityReportResponse:
    delivery = deliveries_repo.get_delivery(session, delivery_id)
    findings = deliveries_repo.list_quality_findings(session, delivery_id)
    return QualityReportResponse(
        delivery=DeliveryItem.model_validate(delivery),
        findings=[QualityFindingItem.model_validate(item) for item in findings],
    )
