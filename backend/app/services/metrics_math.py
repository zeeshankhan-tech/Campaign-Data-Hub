"""Derived metric helpers (CTR / CPC). Stored metrics are sums only."""

from __future__ import annotations

from decimal import Decimal
from typing import Optional

RATIO_QUANTIZE = Decimal("0.000001")


def compute_ctr(clicks: int, impressions: int) -> Optional[Decimal]:
    """Return CTR or None when impressions are zero."""
    if impressions <= 0:
        return None
    return (Decimal(clicks) / Decimal(impressions)).quantize(RATIO_QUANTIZE)


def compute_cpc(spend_usd: Decimal, clicks: int) -> Optional[Decimal]:
    """Return CPC or None when clicks are zero."""
    if clicks <= 0:
        return None
    return (spend_usd / Decimal(clicks)).quantize(RATIO_QUANTIZE)
