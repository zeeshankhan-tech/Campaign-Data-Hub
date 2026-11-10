"""API tests for metrics, deliveries, quality reports, and ingestion."""

from __future__ import annotations

import uuid
from datetime import date, datetime, timezone
from decimal import Decimal
from pathlib import Path

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, delete
from sqlalchemy.orm import Session, sessionmaker

from app.core.config import get_settings
from app.db.models import Delivery, IngestionRun, MetricRow, QualityCheckResult, RejectedRow
from app.db.session import get_db
from app.main import create_app

ASSESSMENT_DATA = Path(__file__).resolve().parents[2] / "assessment" / "data"


@pytest.fixture
def db_session() -> Session:
    settings = get_settings()
    engine = create_engine(settings.database_url, pool_pre_ping=True)
    SessionFactory = sessionmaker(bind=engine, autoflush=False, autocommit=False)
    session = SessionFactory()
    try:
        session.execute(delete(QualityCheckResult))
        session.execute(delete(RejectedRow))
        session.execute(delete(MetricRow))
        session.execute(delete(Delivery))
        session.execute(delete(IngestionRun))
        session.commit()
        yield session
    finally:
        session.close()


@pytest.fixture
def client(db_session: Session) -> TestClient:
    app = create_app()

    def override_get_db():
        try:
            yield db_session
        finally:
            pass

    app.dependency_overrides[get_db] = override_get_db
    return TestClient(app)


def _seed_metrics(session: Session) -> uuid.UUID:
    run = IngestionRun(id=uuid.uuid4(), status="completed")
    session.add(run)
    delivery = Delivery(
        id=uuid.uuid4(),
        platform="meta",
        week_start=date(2026, 6, 29),
        source_filename="meta_ads_2026-06-29.csv",
        health="pass",
        last_run_id=run.id,
        ingested_at=datetime.now(timezone.utc),
    )
    session.add(delivery)
    session.add_all(
        [
            MetricRow(
                id=uuid.uuid4(),
                delivery_id=delivery.id,
                platform="meta",
                campaign="Summer Sale",
                campaign_raw="Summer Sale",
                date=date(2026, 6, 29),
                spend_usd=Decimal("10.000000"),
                impressions=100,
                clicks=0,
                source_filename="meta_ads_2026-06-29.csv",
            ),
            MetricRow(
                id=uuid.uuid4(),
                delivery_id=delivery.id,
                platform="meta",
                campaign="Lead Gen Webinar",
                campaign_raw="Lead Gen Webinar",
                date=date(2026, 6, 30),
                spend_usd=Decimal("20.000000"),
                impressions=200,
                clicks=40,
                source_filename="meta_ads_2026-06-29.csv",
            ),
            MetricRow(
                id=uuid.uuid4(),
                delivery_id=delivery.id,
                platform="google",
                campaign="Search - Brand",
                campaign_raw="Search - Brand",
                date=date(2026, 6, 29),
                spend_usd=Decimal("5.000000"),
                impressions=50,
                clicks=5,
                source_filename="google_ads_2026-06-29.csv",
            ),
        ]
    )
    session.add(
        QualityCheckResult(
            id=uuid.uuid4(),
            delivery_id=delivery.id,
            ingestion_run_id=run.id,
            check_id="numeric_validity",
            severity="info",
            outcome="pass",
            message="ok",
            affected_entities={},
            details={},
        )
    )
    session.commit()
    return delivery.id


def test_metrics_null_cpc_when_clicks_zero(client: TestClient, db_session: Session):
    _seed_metrics(db_session)

    response = client.get("/api/v1/metrics", params={"group_by": "campaign", "platform": "meta"})
    assert response.status_code == 200
    body = response.json()
    assert body["pagination"]["total"] == 2

    by_campaign = {item["campaign"]: item for item in body["items"]}
    assert by_campaign["Summer Sale"]["clicks"] == 0
    assert by_campaign["Summer Sale"]["cpc"] is None
    assert by_campaign["Summer Sale"]["ctr"] == "0.000000"
    assert by_campaign["Lead Gen Webinar"]["cpc"] == "0.500000"

    # Totals include both campaigns: clicks=40, spend=30 => cpc defined
    assert body["totals"]["clicks"] == 40
    assert body["totals"]["cpc"] == "0.750000"


def test_metrics_filter_and_group_by_platform(client: TestClient, db_session: Session):
    _seed_metrics(db_session)
    response = client.get("/api/v1/metrics", params={"group_by": "platform", "limit": 10})
    assert response.status_code == 200
    body = response.json()
    platforms = {item["platform"] for item in body["items"]}
    assert platforms == {"meta", "google"}
    assert body["totals"]["impressions"] == 350


def test_metrics_invalid_date_range(client: TestClient, db_session: Session):
    response = client.get(
        "/api/v1/metrics",
        params={"date_from": "2026-06-30", "date_to": "2026-06-01"},
    )
    assert response.status_code == 422
    assert response.json()["code"] == "validation_error"


def test_deliveries_list_and_quality_report(client: TestClient, db_session: Session):
    delivery_id = _seed_metrics(db_session)

    listed = client.get("/api/v1/deliveries", params={"platform": "meta"})
    assert listed.status_code == 200
    assert listed.json()["pagination"]["total"] == 1

    detail = client.get(f"/api/v1/deliveries/{delivery_id}")
    assert detail.status_code == 200
    assert detail.json()["health"] == "pass"

    report = client.get(f"/api/v1/deliveries/{delivery_id}/quality-report")
    assert report.status_code == 200
    assert report.json()["findings"][0]["check_id"] == "numeric_validity"


def test_delivery_not_found(client: TestClient, db_session: Session):
    missing = uuid.uuid4()
    response = client.get(f"/api/v1/deliveries/{missing}")
    assert response.status_code == 404
    assert response.json()["code"] == "not_found"


def test_ingestion_trigger_and_status(client: TestClient, db_session: Session):
    assert ASSESSMENT_DATA.exists()
    response = client.post(
        "/api/v1/ingestions",
        json={"data_dir": str(ASSESSMENT_DATA)},
    )
    assert response.status_code == 201
    body = response.json()
    assert body["status"] == "completed"
    assert body["accepted_total"] > 0

    status = client.get(f"/api/v1/ingestions/{body['id']}")
    assert status.status_code == 200
    assert status.json()["status"] == "completed"

    metrics = client.get("/api/v1/metrics", params={"group_by": "platform"})
    assert metrics.status_code == 200
    assert metrics.json()["pagination"]["total"] >= 1
