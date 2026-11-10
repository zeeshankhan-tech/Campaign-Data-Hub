"""Persistence helpers for ingestion runs, deliveries, and metrics."""

from __future__ import annotations

import uuid
from datetime import date, datetime, timezone
from typing import Optional

from sqlalchemy import delete
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.orm import Session

from app.db.models import Delivery, IngestionRun, MetricRow, QualityCheckResult, RejectedRow
from app.ingestion.types import NormalizedMetric, RejectedMetric
from app.quality.types import CheckFinding


def create_ingestion_run(session: Session) -> IngestionRun:
    run = IngestionRun(id=uuid.uuid4(), status="running")
    session.add(run)
    session.flush()
    return run


def finish_ingestion_run(
    session: Session,
    run: IngestionRun,
    *,
    status: str,
    summary: dict,
) -> None:
    run.status = status
    run.finished_at = datetime.now(timezone.utc)
    run.summary = summary
    session.add(run)


def upsert_delivery(
    session: Session,
    *,
    platform: str,
    week_start: date,
    source_filename: Optional[str],
    content_checksum: Optional[str],
    health: str,
    run_id: uuid.UUID,
) -> Delivery:
    """Insert or update a delivery by (platform, week_start)."""
    stmt = (
        insert(Delivery)
        .values(
            id=uuid.uuid4(),
            platform=platform,
            week_start=week_start,
            source_filename=source_filename,
            content_checksum=content_checksum,
            health=health,
            last_run_id=run_id,
            ingested_at=datetime.now(timezone.utc),
        )
        .on_conflict_do_update(
            constraint="uq_deliveries_platform_week",
            set_={
                "source_filename": source_filename,
                "content_checksum": content_checksum,
                "health": health,
                "last_run_id": run_id,
                "ingested_at": datetime.now(timezone.utc),
            },
        )
        .returning(Delivery.id)
    )
    delivery_id = session.execute(stmt).scalar_one()
    delivery = session.get(Delivery, delivery_id)
    assert delivery is not None
    return delivery


def replace_delivery_rows(
    session: Session,
    delivery: Delivery,
    *,
    accepted: list[NormalizedMetric],
    rejected: list[RejectedMetric],
) -> None:
    """
    Replace accepted/rejected rows for a delivery with the latest parse result.

    Steps:
    1. Delete previous rejected rows for this delivery.
    2. Delete previous accepted metrics for this delivery.
    3. Upsert the new accepted metrics on UNIQUE(platform, campaign, date).

    The delete+upsert sequence makes re-ingestion authoritative for the week:
    rows that disappear from the source are removed; duplicates collapse via
    the unique constraint.
    """
    session.execute(delete(RejectedRow).where(RejectedRow.delivery_id == delivery.id))
    session.execute(delete(MetricRow).where(MetricRow.delivery_id == delivery.id))

    for metric in accepted:
        stmt = (
            insert(MetricRow)
            .values(
                id=uuid.uuid4(),
                delivery_id=delivery.id,
                platform=metric.platform,
                campaign=metric.campaign,
                campaign_raw=metric.campaign_raw,
                date=metric.date,
                spend_usd=metric.spend_usd,
                impressions=metric.impressions,
                clicks=metric.clicks,
                source_filename=metric.source_filename,
            )
            .on_conflict_do_update(
                constraint="uq_metric_rows_platform_campaign_date",
                set_={
                    "delivery_id": delivery.id,
                    "campaign_raw": metric.campaign_raw,
                    "spend_usd": metric.spend_usd,
                    "impressions": metric.impressions,
                    "clicks": metric.clicks,
                    "source_filename": metric.source_filename,
                },
            )
        )
        session.execute(stmt)

    for item in rejected:
        session.add(
            RejectedRow(
                id=uuid.uuid4(),
                delivery_id=delivery.id,
                platform=item.platform,
                source_filename=item.source_filename,
                source_row_number=item.source_row_number,
                raw_payload=item.raw_payload,
                reason_code=item.reason_code,
                message=item.message,
            )
        )


def replace_quality_findings(
    session: Session,
    *,
    delivery: Delivery,
    run_id: uuid.UUID,
    findings: list[CheckFinding],
) -> None:
    """
    Replace quality findings for a delivery.

    Deletes all prior findings for the delivery so re-ingestion does not
    accumulate duplicate quality results (NFR-1 / ADR-005).
    """
    session.execute(
        delete(QualityCheckResult).where(QualityCheckResult.delivery_id == delivery.id)
    )
    for finding in findings:
        session.add(
            QualityCheckResult(
                id=uuid.uuid4(),
                delivery_id=delivery.id,
                ingestion_run_id=run_id,
                check_id=finding.check_id,
                severity=finding.severity,
                outcome=finding.outcome,
                message=finding.message,
                affected_entities=finding.affected_entities,
                details=finding.details,
            )
        )

