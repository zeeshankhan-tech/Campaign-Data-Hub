"""Explicit quality-check registry (no plugin magic)."""

from __future__ import annotations

from app.quality.checks.campaign_name_hygiene import CampaignNameHygieneCheck
from app.quality.checks.duplicate_or_resend_file import DuplicateOrResendFileCheck
from app.quality.checks.duplicate_rows import DuplicateRowsCheck
from app.quality.checks.missing_expected_delivery import MissingExpectedDeliveryCheck
from app.quality.checks.rejected_reason import RejectedReasonCheck
from app.quality.types import QualityCheck

# Delivery-scoped checks run for each processed delivery.
DELIVERY_CHECKS: list[QualityCheck] = [
    DuplicateOrResendFileCheck(),
    DuplicateRowsCheck(),
    RejectedReasonCheck(
        check_id="schema_required_fields",
        severity="error",
        reason_codes=frozenset(
            {
                "missing_campaign",
                "missing_date",
                "missing_spend",
                "missing_impressions",
                "missing_clicks",
            }
        ),
        pass_message="Required fields present for all rows",
        fail_message="{count} row(s) missing required fields",
    ),
    RejectedReasonCheck(
        check_id="date_parse_or_calendar",
        severity="error",
        reason_codes=frozenset({"invalid_date"}),
        pass_message="All dates parsed successfully",
        fail_message="{count} row(s) have invalid dates",
        extra_row_fields=lambda payload: {"date_raw": payload.get("date_raw")},
    ),
    RejectedReasonCheck(
        check_id="numeric_validity",
        severity="error",
        reason_codes=frozenset(
            {
                "negative_spend",
                "negative_impressions",
                "negative_clicks",
                "invalid_spend",
                "invalid_impressions",
                "invalid_clicks",
            }
        ),
        pass_message="Numeric fields are valid",
        fail_message="{count} row(s) failed numeric validity",
    ),
    RejectedReasonCheck(
        check_id="spend_magnitude_anomaly",
        severity="error",
        reason_codes=frozenset({"spend_magnitude_anomaly"}),
        pass_message="No spend magnitude anomalies detected",
        fail_message=(
            "{count} row(s) have anomalous spend magnitude "
            "(no auto unit correction applied)"
        ),
        extra_row_fields=lambda payload: {
            "spend_amount_raw": payload.get("spend_amount_raw"),
        },
    ),
    CampaignNameHygieneCheck(),
]

# Cadence / cross-delivery checks run once per ingestion run.
CADENCE_CHECKS: list[QualityCheck] = [
    MissingExpectedDeliveryCheck(),
]


def registered_check_ids() -> list[str]:
    """Return all registered check ids for documentation/tests."""
    return [c.check_id for c in DELIVERY_CHECKS + CADENCE_CHECKS]
