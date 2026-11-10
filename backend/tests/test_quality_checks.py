"""Unit tests for independent quality checks and registry extensibility."""

from datetime import date
from decimal import Decimal

from app.ingestion.normalize import normalize_rows
from app.ingestion.types import DeliveryFileRef, RawDeliveryRow
from app.quality.engine import run_checks
from app.quality.health import derive_health
from app.quality.registry import DELIVERY_CHECKS, registered_check_ids
from app.quality.types import CheckFinding, DeliveryCheckContext


FX = {"USD": Decimal("1.0"), "EUR": Decimal("1.08")}


def _ctx_from_rows(
    *,
    platform: str,
    week_start: date,
    filename: str,
    raw_rows: list[RawDeliveryRow],
    file_refs: list[DeliveryFileRef] | None = None,
) -> DeliveryCheckContext:
    accepted, rejected = normalize_rows(raw_rows, FX)
    refs = file_refs or [
        DeliveryFileRef(
            path=filename,
            filename=filename,
            platform=platform,
            week_start=week_start,
            is_resend="_resend" in filename,
        )
    ]
    return DeliveryCheckContext(
        platform=platform,
        week_start=week_start,
        file_refs=refs,
        authoritative_filename=filename,
        content_checksum="abc",
        raw_rows=raw_rows,
        accepted=accepted,
        rejected=rejected,
    )


def test_spend_magnitude_anomaly_check_detects_meta_scale_bug():
    rows = [
        RawDeliveryRow(
            platform="meta",
            source_filename="meta_ads_2026-06-08.csv",
            source_row_number=2,
            campaign_raw="Summer Sale",
            date_raw="06/08/2026",
            spend_amount_raw="17334.00",
            currency="USD",
            impressions_raw="70881",
            clicks_raw="2243",
        )
    ]
    ctx = _ctx_from_rows(
        platform="meta",
        week_start=date(2026, 6, 8),
        filename="meta_ads_2026-06-08.csv",
        raw_rows=rows,
    )
    findings = run_checks(DELIVERY_CHECKS, ctx)
    failed = [f for f in findings if f.check_id == "spend_magnitude_anomaly" and f.outcome == "fail"]
    assert failed
    assert derive_health(findings) == "fail"


def test_duplicate_or_resend_file_check():
    rows = [
        RawDeliveryRow(
            platform="google",
            source_filename="google_ads_2026-06-15_resend.csv",
            source_row_number=2,
            campaign_raw="Search - Brand",
            date_raw="2026-06-15",
            spend_amount_raw="94980000",
            currency="USD",
            impressions_raw="23675",
            clicks_raw="268",
            extras={"unit": "micros"},
        )
    ]
    refs = [
        DeliveryFileRef(
            path="google_ads_2026-06-15.csv",
            filename="google_ads_2026-06-15.csv",
            platform="google",
            week_start=date(2026, 6, 15),
            is_resend=False,
        ),
        DeliveryFileRef(
            path="google_ads_2026-06-15_resend.csv",
            filename="google_ads_2026-06-15_resend.csv",
            platform="google",
            week_start=date(2026, 6, 15),
            is_resend=True,
        ),
    ]
    ctx = _ctx_from_rows(
        platform="google",
        week_start=date(2026, 6, 15),
        filename="google_ads_2026-06-15_resend.csv",
        raw_rows=rows,
        file_refs=refs,
    )
    findings = run_checks(DELIVERY_CHECKS, ctx)
    assert any(f.check_id == "duplicate_or_resend_file" and f.outcome == "fail" for f in findings)


def test_campaign_name_hygiene_detects_case_and_whitespace():
    rows = [
        RawDeliveryRow(
            platform="meta",
            source_filename="meta_ads_2026-06-01.csv",
            source_row_number=12,
            campaign_raw="brand awareness q2",
            date_raw="06/02/2026",
            spend_amount_raw="100.00",
            currency="USD",
            impressions_raw="1000",
            clicks_raw="10",
        ),
        RawDeliveryRow(
            platform="meta",
            source_filename="meta_ads_2026-06-01.csv",
            source_row_number=13,
            campaign_raw="Brand Awareness Q2  ",
            date_raw="06/03/2026",
            spend_amount_raw="100.00",
            currency="USD",
            impressions_raw="1000",
            clicks_raw="10",
        ),
    ]
    ctx = _ctx_from_rows(
        platform="meta",
        week_start=date(2026, 6, 1),
        filename="meta_ads_2026-06-01.csv",
        raw_rows=rows,
    )
    findings = run_checks(DELIVERY_CHECKS, ctx)
    hygiene = next(f for f in findings if f.check_id == "campaign_name_hygiene")
    assert hygiene.outcome == "fail"
    assert hygiene.severity == "warn"


def test_adding_new_check_does_not_modify_existing_checks():
    """Extensibility: append a new check locally without changing registry modules."""

    class AlwaysFailCheck:
        check_id = "always_fail_example"

        def run(self, context):  # noqa: ANN001
            return [
                CheckFinding(
                    check_id=self.check_id,
                    severity="warn",
                    outcome="fail",
                    message="example extension check",
                )
            ]

    before_ids = registered_check_ids()
    extended = list(DELIVERY_CHECKS) + [AlwaysFailCheck()]
    ctx = _ctx_from_rows(
        platform="meta",
        week_start=date(2026, 6, 29),
        filename="meta_ads_2026-06-29.csv",
        raw_rows=[
            RawDeliveryRow(
                platform="meta",
                source_filename="meta_ads_2026-06-29.csv",
                source_row_number=2,
                campaign_raw="Summer Sale",
                date_raw="06/29/2026",
                spend_amount_raw="220.09",
                currency="USD",
                impressions_raw="51175",
                clicks_raw="1520",
            )
        ],
    )
    findings = run_checks(extended, ctx)
    assert any(f.check_id == "always_fail_example" for f in findings)
    # Production registry unchanged.
    assert registered_check_ids() == before_ids
    assert "always_fail_example" not in before_ids
