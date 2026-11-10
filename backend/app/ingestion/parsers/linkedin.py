"""LinkedIn Ads JSON parser."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from app.ingestion.types import RawDeliveryRow


def parse_linkedin_json(path: Path) -> list[RawDeliveryRow]:
    """Parse a LinkedIn delivery JSON array into raw rows."""
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, list):
        raise ValueError(f"{path.name}: root JSON value must be an array")

    rows: list[RawDeliveryRow] = []
    for index, item in enumerate(payload, start=1):
        if not isinstance(item, dict):
            raise ValueError(f"{path.name}: item {index} is not an object")
        spend: dict[str, Any] = item.get("spend") if isinstance(item.get("spend"), dict) else {}
        rows.append(
            RawDeliveryRow(
                platform="linkedin",
                source_filename=path.name,
                source_row_number=index,
                campaign_raw=item.get("campaign"),
                date_raw=item.get("date_ts"),
                spend_amount_raw=spend.get("amount"),
                currency=str(spend.get("currency") or "").strip().upper(),
                impressions_raw=item.get("impressions"),
                clicks_raw=item.get("clicks"),
                extras={"date_kind": "epoch_ms"},
            )
        )
    return rows
