"""Logical identity and idempotency keys (Phase 5 / ADR-002)."""

from __future__ import annotations

from datetime import date

from app.ingestion.types import NormalizedMetric

# Delivery natural key: one logical weekly delivery per platform.
# Resend filenames map to the same key via discovery (week_start extraction).
DeliveryKey = tuple[str, date]

# Accepted metric natural key used for UNIQUE(platform, campaign, date).
MetricKey = tuple[str, str, date]


def delivery_key(platform: str, week_start: date) -> DeliveryKey:
    """Return the idempotent delivery identity."""
    return (platform, week_start)


def metric_key(metric: NormalizedMetric) -> MetricKey:
    """Return the idempotent accepted-metric identity."""
    return (metric.platform, metric.campaign, metric.date)


def metric_key_from_parts(platform: str, campaign: str, metric_date: date) -> MetricKey:
    """Build a metric key from parts (campaign must already be stripped)."""
    return (platform, campaign, metric_date)
