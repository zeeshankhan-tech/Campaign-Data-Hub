"""Phase 5 reliability tests: idempotency, isolation, constraints."""

from __future__ import annotations

import uuid
from datetime import date
from decimal import Decimal
from pathlib import Path
from unittest.mock import patch

import pytest
from sqlalchemy import create_engine, func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session, sessionmaker

from app.core.config import get_settings
from app.db.models import Delivery, IngestionRun, MetricRow, QualityCheckResult, RejectedRow
from app.ingestion.identity import delivery_key, metric_key_from_parts
from app.ingestion.normalize import normalize_rows
from app.ingestion.pipeline import run_ingestion
from app.ingestion.types import RawDeliveryRow

ASSESSMENT_DATA = Path(__file__).resolve().parents[2] / "assessment" / "data"
FX = {"USD": Decimal("1.0"), "EUR": Decimal("1.08")}


@pytest.fixture
def db_session() -> Session:
    settings = get_settings()
    engine = create_engine(settings.database_url, pool_pre_ping=True)
    SessionFactory = sessionmaker(bind=engine, autoflush=False, autocommit=False)
    session = SessionFactory()
    try:
        session.query(QualityCheckResult).delete()
        session.query(RejectedRow).delete()
        session.query(MetricRow).delete()
        session.query(Delivery).delete()
        session.query(IngestionRun).delete()
        session.commit()
        yield session
    finally:
        session.close()


def test_identity_helpers():
    assert delivery_key("google", date(2026, 6, 15)) == ("google", date(2026, 6, 15))
    assert metric_key_from_parts("meta", "Summer Sale", date(2026, 6, 1)) == (
        "meta",
        "Summer Sale",
        date(2026, 6, 1),
    )


def test_mixed_valid_and_invalid_rows_are_isolated():
    rows = [
        RawDeliveryRow(
            platform="meta",
            source_filename="mixed.csv",
            source_row_number=2,
            campaign_raw="Summer Sale",
            date_raw="06/01/2026",
            spend_amount_raw="100.00",
            currency="USD",
            impressions_raw="1000",
            clicks_raw="10",
        ),
        RawDeliveryRow(
            platform="meta",
            source_filename="mixed.csv",
            source_row_number=3,
            campaign_raw="Summer Sale",
            date_raw="06/31/2026",
            spend_amount_raw="100.00",
            currency="USD",
            impressions_raw="1000",
            clicks_raw="10",
        ),
        RawDeliveryRow(
            platform="meta",
            source_filename="mixed.csv",
            source_row_number=4,
            campaign_raw="Lead Gen Webinar",
            date_raw="06/02/2026",
            spend_amount_raw="50.00",
            currency="USD",
            impressions_raw="500",
            clicks_raw="",
        ),
    ]
    accepted, rejected = normalize_rows(rows, FX)
    assert len(accepted) == 1
    assert accepted[0].campaign == "Summer Sale"
    assert {item.reason_code for item in rejected} == {"invalid_date", "missing_clicks"}


def test_triple_reingest_does_not_duplicate_metrics_or_quality(db_session: Session):
    assert ASSESSMENT_DATA.exists()

    first = run_ingestion(db_session, data_dir=ASSESSMENT_DATA)
    second = run_ingestion(db_session, data_dir=ASSESSMENT_DATA)
    third = run_ingestion(db_session, data_dir=ASSESSMENT_DATA)

    assert first.status == second.status == third.status == "completed"
    assert first.accepted_total == second.accepted_total == third.accepted_total

    metric_count = db_session.scalar(select(func.count()).select_from(MetricRow))
    delivery_count = db_session.scalar(select(func.count()).select_from(Delivery))
    quality_count = db_session.scalar(select(func.count()).select_from(QualityCheckResult))

    assert metric_count == first.accepted_total
    # 14 file-backed deliveries + 1 missing LinkedIn week marker
    assert delivery_count == 15
    # Findings are replaced per delivery (no unbounded growth across runs).
    assert quality_count > 0
    assert quality_count == db_session.scalar(
        select(func.count()).select_from(QualityCheckResult)
    )

    # Running again still keeps quality_count stable.
    fourth = run_ingestion(db_session, data_dir=ASSESSMENT_DATA)
    assert fourth.status == "completed"
    quality_after = db_session.scalar(select(func.count()).select_from(QualityCheckResult))
    assert quality_after == quality_count


def test_metric_unique_constraint_enforced(db_session: Session):
    delivery = Delivery(
        id=uuid.uuid4(),
        platform="meta",
        week_start=date(2026, 6, 29),
        source_filename="meta_ads_2026-06-29.csv",
        health="pass",
    )
    db_session.add(delivery)
    db_session.flush()

    shared = dict(
        delivery_id=delivery.id,
        platform="meta",
        campaign="Summer Sale",
        campaign_raw="Summer Sale",
        date=date(2026, 6, 29),
        spend_usd=Decimal("1.000000"),
        impressions=1,
        clicks=1,
        source_filename="meta_ads_2026-06-29.csv",
    )
    db_session.add(MetricRow(id=uuid.uuid4(), **shared))
    db_session.commit()

    db_session.add(MetricRow(id=uuid.uuid4(), **shared))
    with pytest.raises(IntegrityError):
        db_session.commit()
    db_session.rollback()


def test_delivery_unique_constraint_enforced(db_session: Session):
    db_session.add(
        Delivery(
            id=uuid.uuid4(),
            platform="linkedin",
            week_start=date(2026, 6, 22),
            health="fail",
        )
    )
    db_session.commit()

    db_session.add(
        Delivery(
            id=uuid.uuid4(),
            platform="linkedin",
            week_start=date(2026, 6, 22),
            health="fail",
        )
    )
    with pytest.raises(IntegrityError):
        db_session.commit()
    db_session.rollback()


def test_file_processing_failure_isolates_and_preserves_other_deliveries(db_session: Session):
    """A hard failure on one delivery must not erase already-committed siblings."""
    assert ASSESSMENT_DATA.exists()

    baseline = run_ingestion(db_session, data_dir=ASSESSMENT_DATA)
    assert baseline.status == "completed"
    baseline_metrics = db_session.scalar(select(func.count()).select_from(MetricRow))
    assert baseline_metrics > 0

    # Fail only while processing Meta week 2026-06-08; other deliveries continue.
    real_normalize = normalize_rows

    def boom_for_meta_week(raw_rows, fx_rates):  # noqa: ANN001
        if raw_rows and raw_rows[0].platform == "meta" and "2026-06-08" in raw_rows[0].source_filename:
            raise RuntimeError("simulated infrastructure failure")
        return real_normalize(raw_rows, fx_rates)

    with patch("app.ingestion.pipeline.normalize_rows", side_effect=boom_for_meta_week):
        result = run_ingestion(db_session, data_dir=ASSESSMENT_DATA)

    assert result.status == "completed"
    meta_fail = next(
        d
        for d in result.deliveries
        if d.platform == "meta" and d.week_start == date(2026, 6, 8)
    )
    assert meta_fail.health == "fail"
    assert meta_fail.error is not None

    # Other platforms still have accepted metrics after the isolated failure.
    google_metrics = db_session.scalar(
        select(func.count()).select_from(MetricRow).where(MetricRow.platform == "google")
    )
    assert google_metrics > 0
    assert "failure_classes" in result.summary
