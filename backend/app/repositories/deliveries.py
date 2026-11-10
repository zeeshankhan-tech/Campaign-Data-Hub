"""Query helpers for deliveries and quality findings."""

from __future__ import annotations

from typing import Optional
from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.db.models import Delivery, QualityCheckResult
from app.core.exceptions import NotFoundError


def list_deliveries(
    session: Session,
    *,
    platform: Optional[str],
    health: Optional[str],
    limit: int,
    offset: int,
) -> tuple[list[Delivery], int]:
    stmt = select(Delivery)
    count_stmt = select(func.count()).select_from(Delivery)
    if platform:
        stmt = stmt.where(Delivery.platform == platform)
        count_stmt = count_stmt.where(Delivery.platform == platform)
    if health:
        stmt = stmt.where(Delivery.health == health)
        count_stmt = count_stmt.where(Delivery.health == health)

    total = session.execute(count_stmt).scalar_one()
    rows = session.execute(
        stmt.order_by(Delivery.week_start.desc(), Delivery.platform).limit(limit).offset(offset)
    ).scalars().all()
    return list(rows), int(total)


def get_delivery(session: Session, delivery_id: UUID) -> Delivery:
    delivery = session.get(Delivery, delivery_id)
    if delivery is None:
        raise NotFoundError(f"Delivery {delivery_id} not found")
    return delivery


def list_quality_findings(session: Session, delivery_id: UUID) -> list[QualityCheckResult]:
    return list(
        session.execute(
            select(QualityCheckResult)
            .where(QualityCheckResult.delivery_id == delivery_id)
            .order_by(QualityCheckResult.check_id, QualityCheckResult.outcome)
        ).scalars().all()
    )
