"""Deliveries and quality-report API schemas."""

from __future__ import annotations

from datetime import date, datetime
from typing import Any, Optional
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

from app.api.schemas.common import PaginationMeta


class DeliveryItem(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    platform: str
    week_start: date
    source_filename: Optional[str] = None
    content_checksum: Optional[str] = None
    health: str
    ingested_at: datetime
    last_run_id: Optional[UUID] = None


class DeliveryListResponse(BaseModel):
    items: list[DeliveryItem]
    pagination: PaginationMeta


class QualityFindingItem(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    check_id: str
    severity: str
    outcome: str
    message: str
    affected_entities: Optional[dict[str, Any]] = None
    details: Optional[dict[str, Any]] = None


class QualityReportResponse(BaseModel):
    delivery: DeliveryItem
    findings: list[QualityFindingItem]
