"""Normalization and row-validation rules (ADR-002)."""

from __future__ import annotations

from datetime import date, datetime, timezone
from decimal import Decimal, InvalidOperation
from typing import Optional

from app.ingestion.identity import metric_key
from app.ingestion.types import NormalizedMetric, RawDeliveryRow, RejectedMetric

MICROS_PER_UNIT = Decimal("1000000")
SPEND_QUANTIZE = Decimal("0.000001")

# Meta week 2026-06-08 anomaly: peer weeks are ~$40–$280. Values above this
# threshold are rejected (not auto-scaled). Tunable constant documented here.
META_SPEND_USD_MAX_ACCEPTED = Decimal("1000")


def _reject(
    raw: RawDeliveryRow,
    reason_code: str,
    message: str,
) -> RejectedMetric:
    return RejectedMetric(
        platform=raw.platform,
        source_filename=raw.source_filename,
        source_row_number=raw.source_row_number,
        reason_code=reason_code,
        message=message,
        raw_payload={
            "campaign_raw": raw.campaign_raw,
            "date_raw": raw.date_raw,
            "spend_amount_raw": raw.spend_amount_raw,
            "currency": raw.currency,
            "impressions_raw": raw.impressions_raw,
            "clicks_raw": raw.clicks_raw,
            "extras": raw.extras,
        },
    )


def _parse_campaign(raw: RawDeliveryRow) -> tuple[Optional[str], Optional[str], Optional[RejectedMetric]]:
    if raw.campaign_raw is None or str(raw.campaign_raw).strip() == "":
        return None, None, _reject(raw, "missing_campaign", "campaign is missing")
    campaign_raw = str(raw.campaign_raw)
    return campaign_raw.strip(), campaign_raw, None


def _parse_meta_date(value: object) -> date:
    text = str(value).strip()
    return datetime.strptime(text, "%m/%d/%Y").date()


def _parse_google_date(value: object) -> date:
    text = str(value).strip()
    return datetime.strptime(text, "%Y-%m-%d").date()


def _parse_linkedin_date(value: object) -> date:
    ts = int(value)
    return datetime.fromtimestamp(ts / 1000, tz=timezone.utc).date()


def _parse_date(raw: RawDeliveryRow) -> tuple[Optional[date], Optional[RejectedMetric]]:
    if raw.date_raw is None or str(raw.date_raw).strip() == "":
        return None, _reject(raw, "missing_date", "date is missing")
    try:
        if raw.platform == "meta":
            return _parse_meta_date(raw.date_raw), None
        if raw.platform == "google":
            return _parse_google_date(raw.date_raw), None
        if raw.platform == "linkedin":
            return _parse_linkedin_date(raw.date_raw), None
        return None, _reject(raw, "unsupported_platform", f"unsupported platform {raw.platform}")
    except (ValueError, TypeError, OSError, OverflowError) as exc:
        return None, _reject(raw, "invalid_date", f"could not parse date {raw.date_raw!r}: {exc}")


def _parse_int_field(
    raw: RawDeliveryRow,
    value: object,
    field_name: str,
    *,
    allow_missing: bool = False,
) -> tuple[Optional[int], Optional[RejectedMetric]]:
    if value is None or (isinstance(value, str) and value.strip() == ""):
        if allow_missing:
            return None, None
        return None, _reject(raw, f"missing_{field_name}", f"{field_name} is missing")
    try:
        number = int(str(value).strip())
    except (TypeError, ValueError):
        return None, _reject(raw, f"invalid_{field_name}", f"{field_name} is not an integer: {value!r}")
    if number < 0:
        return None, _reject(raw, f"negative_{field_name}", f"{field_name} is negative: {number}")
    return number, None


def _to_decimal(value: object) -> Decimal:
    return Decimal(str(value).strip())


def _parse_spend_usd(
    raw: RawDeliveryRow,
    fx_rates: dict[str, Decimal],
) -> tuple[Optional[Decimal], Optional[RejectedMetric]]:
    if raw.spend_amount_raw is None or str(raw.spend_amount_raw).strip() == "":
        return None, _reject(raw, "missing_spend", "spend amount is missing")

    currency = (raw.currency or "").upper()
    if currency not in fx_rates:
        return None, _reject(raw, "unknown_currency", f"no FX rate for currency {currency!r}")

    try:
        if raw.platform == "google" or raw.extras.get("unit") == "micros":
            micros = Decimal(str(raw.spend_amount_raw).strip())
            if micros != micros.to_integral_value():
                return None, _reject(raw, "invalid_spend", f"micros must be integral: {raw.spend_amount_raw!r}")
            amount = micros / MICROS_PER_UNIT
        else:
            amount = _to_decimal(raw.spend_amount_raw)
    except (InvalidOperation, ValueError):
        return None, _reject(raw, "invalid_spend", f"spend is not numeric: {raw.spend_amount_raw!r}")

    spend_usd = (amount * fx_rates[currency]).quantize(SPEND_QUANTIZE)
    if spend_usd < 0:
        return None, _reject(raw, "negative_spend", f"spend_usd is negative: {spend_usd}")

    if raw.platform == "meta" and spend_usd > META_SPEND_USD_MAX_ACCEPTED:
        return None, _reject(
            raw,
            "spend_magnitude_anomaly",
            (
                f"meta spend_usd {spend_usd} exceeds accepted max "
                f"{META_SPEND_USD_MAX_ACCEPTED} (no auto unit correction)"
            ),
        )

    return spend_usd, None


def normalize_row(
    raw: RawDeliveryRow,
    fx_rates: dict[str, Decimal],
) -> NormalizedMetric | RejectedMetric:
    """Normalize one raw row into an accepted metric or a rejection."""
    campaign, campaign_raw, campaign_error = _parse_campaign(raw)
    if campaign_error:
        return campaign_error

    parsed_date, date_error = _parse_date(raw)
    if date_error:
        return date_error

    spend_usd, spend_error = _parse_spend_usd(raw, fx_rates)
    if spend_error:
        return spend_error

    impressions, impressions_error = _parse_int_field(raw, raw.impressions_raw, "impressions")
    if impressions_error:
        return impressions_error

    clicks, clicks_error = _parse_int_field(raw, raw.clicks_raw, "clicks")
    if clicks_error:
        return clicks_error

    assert campaign is not None and campaign_raw is not None
    assert parsed_date is not None and spend_usd is not None
    assert impressions is not None and clicks is not None

    return NormalizedMetric(
        platform=raw.platform,
        campaign=campaign,
        campaign_raw=campaign_raw,
        date=parsed_date,
        spend_usd=spend_usd,
        impressions=impressions,
        clicks=clicks,
        source_filename=raw.source_filename,
        source_row_number=raw.source_row_number,
    )


def normalize_rows(
    raw_rows: list[RawDeliveryRow],
    fx_rates: dict[str, Decimal],
) -> tuple[list[NormalizedMetric], list[RejectedMetric]]:
    """
    Normalize many rows.

    Exact duplicate logical keys `(platform, campaign, date)` collapse to the
    last accepted occurrence (idempotent within a file).
    """
    accepted_by_key: dict[tuple[str, str, date], NormalizedMetric] = {}
    rejected: list[RejectedMetric] = []

    for raw in raw_rows:
        result = normalize_row(raw, fx_rates)
        if isinstance(result, RejectedMetric):
            rejected.append(result)
            continue
        accepted_by_key[metric_key(result)] = result

    return list(accepted_by_key.values()), rejected
