"""Unit tests for normalization and derived metrics."""

from datetime import date
from decimal import Decimal

from app.ingestion.normalize.rules import normalize_row, normalize_rows
from app.ingestion.types import NormalizedMetric, RawDeliveryRow, RejectedMetric
from app.services.metrics_math import compute_cpc, compute_ctr

FX = {"USD": Decimal("1.0"), "EUR": Decimal("1.08")}


def _meta(**overrides):
    base = dict(
        platform="meta",
        source_filename="meta_ads_2026-06-01.csv",
        source_row_number=2,
        campaign_raw="Summer Sale",
        date_raw="06/01/2026",
        spend_amount_raw="200.08",
        currency="USD",
        impressions_raw="37215",
        clicks_raw="574",
    )
    base.update(overrides)
    return RawDeliveryRow(**base)


def _google(**overrides):
    base = dict(
        platform="google",
        source_filename="google_ads_2026-06-01.csv",
        source_row_number=2,
        campaign_raw="Search - Brand",
        date_raw="2026-06-07",
        spend_amount_raw="117410000",
        currency="USD",
        impressions_raw="37355",
        clicks_raw="779",
        extras={"unit": "micros"},
    )
    base.update(overrides)
    return RawDeliveryRow(**base)


def _linkedin(**overrides):
    base = dict(
        platform="linkedin",
        source_filename="linkedin_ads_2026-06-01.json",
        source_row_number=1,
        campaign_raw="ABM Tier 1",
        date_raw=1780272000000,
        spend_amount_raw="92.37",
        currency="EUR",
        impressions_raw=41097,
        clicks_raw=1283,
        extras={"date_kind": "epoch_ms"},
    )
    base.update(overrides)
    return RawDeliveryRow(**base)


def test_google_micros_to_usd():
    result = normalize_row(_google(), FX)
    assert isinstance(result, NormalizedMetric)
    assert result.spend_usd == Decimal("117.410000")
    assert result.date == date(2026, 6, 7)


def test_linkedin_eur_fx_and_epoch_date():
    result = normalize_row(_linkedin(), FX)
    assert isinstance(result, NormalizedMetric)
    assert result.spend_usd == Decimal("99.759600")  # 92.37 * 1.08
    assert result.date == date(2026, 6, 1)


def test_meta_campaign_strip_preserves_raw():
    result = normalize_row(_meta(campaign_raw="Brand Awareness Q2  "), FX)
    assert isinstance(result, NormalizedMetric)
    assert result.campaign == "Brand Awareness Q2"
    assert result.campaign_raw == "Brand Awareness Q2  "


def test_meta_invalid_calendar_date_rejected():
    result = normalize_row(_meta(date_raw="06/31/2026"), FX)
    assert isinstance(result, RejectedMetric)
    assert result.reason_code == "invalid_date"


def test_meta_iso_date_rejected_as_invalid_format():
    result = normalize_row(_meta(date_raw="2026-06-01"), FX)
    assert isinstance(result, RejectedMetric)
    assert result.reason_code == "invalid_date"


def test_meta_magnitude_anomaly_rejected():
    result = normalize_row(_meta(spend_amount_raw="17334.00"), FX)
    assert isinstance(result, RejectedMetric)
    assert result.reason_code == "spend_magnitude_anomaly"


def test_meta_negative_spend_rejected():
    result = normalize_row(_meta(spend_amount_raw="-111.41"), FX)
    assert isinstance(result, RejectedMetric)
    assert result.reason_code == "negative_spend"


def test_missing_clicks_rejected():
    result = normalize_row(_meta(clicks_raw=""), FX)
    assert isinstance(result, RejectedMetric)
    assert result.reason_code == "missing_clicks"


def test_duplicate_logical_keys_collapse():
    rows = [
        _google(source_row_number=2),
        _google(source_row_number=25),
    ]
    accepted, rejected = normalize_rows(rows, FX)
    assert rejected == []
    assert len(accepted) == 1


def test_ctr_and_cpc_undefined_when_denominator_zero():
    assert compute_ctr(clicks=10, impressions=0) is None
    assert compute_cpc(spend_usd=Decimal("12.50"), clicks=0) is None
    assert compute_ctr(clicks=1, impressions=4) == Decimal("0.250000")
    assert compute_cpc(spend_usd=Decimal("10"), clicks=4) == Decimal("2.500000")
