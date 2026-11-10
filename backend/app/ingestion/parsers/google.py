"""Google Ads CSV parser."""

from __future__ import annotations

import csv
from pathlib import Path

from app.ingestion.types import RawDeliveryRow

REQUIRED_HEADERS = ["Campaign", "Day", "Cost (micros)", "Currency", "Impr.", "Clicks"]


def parse_google_csv(path: Path) -> list[RawDeliveryRow]:
    """Parse a Google delivery CSV into raw rows."""
    with path.open(newline="", encoding="utf-8") as handle:
        reader = csv.DictReader(handle)
        if reader.fieldnames is None:
            raise ValueError(f"{path.name}: missing CSV header")
        missing = [h for h in REQUIRED_HEADERS if h not in reader.fieldnames]
        if missing:
            raise ValueError(f"{path.name}: missing columns {missing}")

        rows: list[RawDeliveryRow] = []
        for index, row in enumerate(reader, start=2):
            rows.append(
                RawDeliveryRow(
                    platform="google",
                    source_filename=path.name,
                    source_row_number=index,
                    campaign_raw=row.get("Campaign"),
                    date_raw=row.get("Day"),
                    spend_amount_raw=row.get("Cost (micros)"),
                    currency=(row.get("Currency") or "USD").strip().upper(),
                    impressions_raw=row.get("Impr."),
                    clicks_raw=row.get("Clicks"),
                    extras={"unit": "micros"},
                )
            )
        return rows
