"""Shared DTOs for ingestion and normalization."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date
from decimal import Decimal
from typing import Any, Optional


@dataclass(frozen=True)
class RawDeliveryRow:
    """Platform-agnostic raw row before normalization."""

    platform: str
    source_filename: str
    source_row_number: int
    campaign_raw: Any
    date_raw: Any
    spend_amount_raw: Any
    currency: str
    impressions_raw: Any
    clicks_raw: Any
    extras: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class NormalizedMetric:
    """Canonical accepted metric row."""

    platform: str
    campaign: str
    campaign_raw: str
    date: date
    spend_usd: Decimal
    impressions: int
    clicks: int
    source_filename: str
    source_row_number: int


@dataclass(frozen=True)
class RejectedMetric:
    """Row that failed validation/normalization."""

    platform: str
    source_filename: str
    source_row_number: int
    reason_code: str
    message: str
    raw_payload: dict[str, Any]


@dataclass
class DeliveryFileRef:
    """Discovered delivery file mapped to a logical delivery key."""

    path: str
    filename: str
    platform: str
    week_start: date
    is_resend: bool = False
