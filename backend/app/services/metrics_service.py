"""Metrics application service."""

from __future__ import annotations

from datetime import date
from typing import Literal, Optional

from sqlalchemy.orm import Session

from app.api.schemas.metrics import MetricGroupItem, MetricsResponse, MetricTotals
from app.api.schemas.common import PaginationMeta
from app.core.exceptions import ValidationAppError
from app.repositories import metrics as metrics_repo
from app.services.metrics_math import compute_cpc, compute_ctr

GroupBy = Literal["campaign", "platform"]


def get_metrics(
    session: Session,
    *,
    group_by: GroupBy = "campaign",
    platform: Optional[str] = None,
    date_from: Optional[date] = None,
    date_to: Optional[date] = None,
    limit: int = 100,
    offset: int = 0,
) -> MetricsResponse:
    if date_from and date_to and date_from > date_to:
        raise ValidationAppError("date_from must be on or before date_to")
    if limit < 1 or limit > 500:
        raise ValidationAppError("limit must be between 1 and 500")
    if offset < 0:
        raise ValidationAppError("offset must be >= 0")

    items_raw, totals_raw, total = metrics_repo.aggregate_metrics(
        session,
        group_by=group_by,
        platform=platform,
        date_from=date_from,
        date_to=date_to,
        limit=limit,
        offset=offset,
    )

    items = [
        MetricGroupItem(
            platform=row.get("platform"),
            campaign=row.get("campaign"),
            spend_usd=row["spend_usd"],
            impressions=row["impressions"],
            clicks=row["clicks"],
            ctr=compute_ctr(row["clicks"], row["impressions"]),
            cpc=compute_cpc(row["spend_usd"], row["clicks"]),
        )
        for row in items_raw
    ]
    totals = MetricTotals(
        spend_usd=totals_raw["spend_usd"],
        impressions=totals_raw["impressions"],
        clicks=totals_raw["clicks"],
        ctr=compute_ctr(totals_raw["clicks"], totals_raw["impressions"]),
        cpc=compute_cpc(totals_raw["spend_usd"], totals_raw["clicks"]),
    )
    return MetricsResponse(
        group_by=group_by,
        items=items,
        totals=totals,
        pagination=PaginationMeta(limit=limit, offset=offset, total=total),
    )
