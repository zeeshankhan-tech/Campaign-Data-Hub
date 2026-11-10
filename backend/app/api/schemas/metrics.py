"""Metrics API schemas."""

from __future__ import annotations

from typing import Literal, Optional

from pydantic import BaseModel, Field

from app.api.schemas.common import DecimalStr, OptionalDecimalStr, PaginationMeta

GroupBy = Literal["campaign", "platform"]


class MetricTotals(BaseModel):
    spend_usd: DecimalStr
    impressions: int
    clicks: int
    ctr: OptionalDecimalStr = Field(
        default=None,
        description="clicks / impressions; null when impressions == 0",
    )
    cpc: OptionalDecimalStr = Field(
        default=None,
        description="spend_usd / clicks; null when clicks == 0",
    )


class MetricGroupItem(BaseModel):
    platform: Optional[str] = None
    campaign: Optional[str] = None
    spend_usd: DecimalStr
    impressions: int
    clicks: int
    ctr: OptionalDecimalStr = None
    cpc: OptionalDecimalStr = None


class MetricsResponse(BaseModel):
    group_by: GroupBy
    items: list[MetricGroupItem]
    totals: MetricTotals
    pagination: PaginationMeta
