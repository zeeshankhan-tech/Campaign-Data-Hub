"""Load fixed FX rates from the assessment exchange-rates file."""

from __future__ import annotations

import json
from decimal import Decimal
from pathlib import Path


def load_exchange_rates(path: Path) -> dict[str, Decimal]:
    """
    Load currency → USD multipliers.

    Expected JSON shape:
    `{ "rates": { "USD": 1.0, "EUR": 1.08 } }`
    """
    payload = json.loads(path.read_text(encoding="utf-8"))
    rates_raw = payload.get("rates")
    if not isinstance(rates_raw, dict) or not rates_raw:
        raise ValueError(f"exchange rates file missing rates object: {path}")

    rates: dict[str, Decimal] = {}
    for currency, value in rates_raw.items():
        rates[str(currency).upper()] = Decimal(str(value))
    return rates
