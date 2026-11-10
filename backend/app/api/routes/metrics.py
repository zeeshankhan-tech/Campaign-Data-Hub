"""Campaign metrics endpoints."""

from __future__ import annotations

from datetime import date
from typing import Literal, Optional

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.api.schemas.metrics import MetricsResponse
from app.db.session import get_db
from app.services import metrics_service

router = APIRouter(tags=["metrics"])


@router.get(
    "/metrics",
    response_model=MetricsResponse,
    summary="List aggregated campaign metrics",
)
def get_metrics(
    group_by: Literal["campaign", "platform"] = Query(default="campaign"),
    platform: Optional[str] = Query(default=None),
    date_from: Optional[date] = Query(default=None),
    date_to: Optional[date] = Query(default=None),
    limit: int = Query(default=100, ge=1, le=500),
    offset: int = Query(default=0, ge=0),
    db: Session = Depends(get_db),
) -> MetricsResponse:
    """
    Return normalized metrics grouped by campaign or platform.

    CTR = clicks / impressions (null when impressions == 0).
    CPC = spend_usd / clicks (null when clicks == 0).
    """
    return metrics_service.get_metrics(
        db,
        group_by=group_by,
        platform=platform,
        date_from=date_from,
        date_to=date_to,
        limit=limit,
        offset=offset,
    )
