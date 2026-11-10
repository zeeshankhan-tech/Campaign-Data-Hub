"""Query helpers for aggregated metrics."""

from __future__ import annotations

from datetime import date
from decimal import Decimal
from typing import Any, Literal, Optional

from sqlalchemy import Select, func, select
from sqlalchemy.orm import Session

from app.db.models import MetricRow

GroupBy = Literal["campaign", "platform"]


def _filtered_metrics_stmt(
    *,
    platform: Optional[str],
    date_from: Optional[date],
    date_to: Optional[date],
) -> Select[Any]:
    stmt = select(MetricRow)
    if platform:
        stmt = stmt.where(MetricRow.platform == platform)
    if date_from:
        stmt = stmt.where(MetricRow.date >= date_from)
    if date_to:
        stmt = stmt.where(MetricRow.date <= date_to)
    return stmt


def aggregate_metrics(
    session: Session,
    *,
    group_by: GroupBy,
    platform: Optional[str],
    date_from: Optional[date],
    date_to: Optional[date],
    limit: int,
    offset: int,
) -> tuple[list[dict[str, Any]], dict[str, Any], int]:
    """
    Return (page_items, totals, total_group_count).

    Totals are computed over the full filtered set (not only the current page).
    """
    base = _filtered_metrics_stmt(platform=platform, date_from=date_from, date_to=date_to).subquery()

    totals_row = session.execute(
        select(
            func.coalesce(func.sum(base.c.spend_usd), 0),
            func.coalesce(func.sum(base.c.impressions), 0),
            func.coalesce(func.sum(base.c.clicks), 0),
        )
    ).one()
    totals = {
        "spend_usd": Decimal(str(totals_row[0])),
        "impressions": int(totals_row[1]),
        "clicks": int(totals_row[2]),
    }

    if group_by == "campaign":
        grouped = (
            select(
                base.c.platform.label("platform"),
                base.c.campaign.label("campaign"),
                func.sum(base.c.spend_usd).label("spend_usd"),
                func.sum(base.c.impressions).label("impressions"),
                func.sum(base.c.clicks).label("clicks"),
            )
            .group_by(base.c.platform, base.c.campaign)
            .order_by(func.sum(base.c.spend_usd).desc(), base.c.platform, base.c.campaign)
        )
    else:
        grouped = (
            select(
                base.c.platform.label("platform"),
                func.sum(base.c.spend_usd).label("spend_usd"),
                func.sum(base.c.impressions).label("impressions"),
                func.sum(base.c.clicks).label("clicks"),
            )
            .group_by(base.c.platform)
            .order_by(func.sum(base.c.spend_usd).desc(), base.c.platform)
        )

    grouped_subq = grouped.subquery()
    total_groups = session.execute(select(func.count()).select_from(grouped_subq)).scalar_one()

    page_rows = session.execute(
        select(grouped_subq).limit(limit).offset(offset)
    ).mappings().all()

    items: list[dict[str, Any]] = []
    for row in page_rows:
        item: dict[str, Any] = {
            "platform": row["platform"],
            "spend_usd": Decimal(str(row["spend_usd"])),
            "impressions": int(row["impressions"]),
            "clicks": int(row["clicks"]),
        }
        if group_by == "campaign":
            item["campaign"] = row["campaign"]
        items.append(item)

    return items, totals, int(total_groups)
