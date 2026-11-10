"""Integration tests for ingestion against PostgreSQL."""

from datetime import date
from pathlib import Path

import pytest
from sqlalchemy import create_engine, func, select
from sqlalchemy.orm import Session, sessionmaker

from app.core.config import get_settings
from app.db.models import Delivery, MetricRow, QualityCheckResult, RejectedRow
from app.ingestion.pipeline import run_ingestion

ASSESSMENT_DATA = Path(__file__).resolve().parents[2] / "assessment" / "data"


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
        session.commit()
        yield session
    finally:
        session.close()


def test_ingest_assessment_dataset_persists_accepted_and_rejected(db_session: Session):
    assert ASSESSMENT_DATA.exists(), f"missing assessment data at {ASSESSMENT_DATA}"

    first = run_ingestion(db_session, data_dir=ASSESSMENT_DATA)
    assert first.status == "completed"
    assert first.accepted_total > 0
    assert first.rejected_total > 0

    metric_count = db_session.scalar(select(func.count()).select_from(MetricRow))
    rejected_count = db_session.scalar(select(func.count()).select_from(RejectedRow))
    quality_count = db_session.scalar(select(func.count()).select_from(QualityCheckResult))
    assert metric_count == first.accepted_total
    assert rejected_count >= first.rejected_total
    assert quality_count > 0

    # Missing LinkedIn 2026-06-22 should be marked with quality finding.
    missing = db_session.scalar(
        select(func.count())
        .select_from(Delivery)
        .where(
            Delivery.platform == "linkedin",
            Delivery.week_start == date(2026, 6, 22),
            Delivery.health == "fail",
        )
    )
    assert missing == 1

    missing_finding = db_session.scalar(
        select(func.count())
        .select_from(QualityCheckResult)
        .where(QualityCheckResult.check_id == "missing_expected_delivery")
    )
    assert missing_finding >= 1

    meta_magnitude = db_session.scalar(
        select(func.count())
        .select_from(QualityCheckResult)
        .where(
            QualityCheckResult.check_id == "spend_magnitude_anomaly",
            QualityCheckResult.outcome == "fail",
        )
    )
    assert meta_magnitude >= 1

    # Idempotent re-ingest should not increase accepted metric cardinality.
    second = run_ingestion(db_session, data_dir=ASSESSMENT_DATA)
    assert second.status == "completed"
    metric_count_after = db_session.scalar(select(func.count()).select_from(MetricRow))
    assert metric_count_after == metric_count
