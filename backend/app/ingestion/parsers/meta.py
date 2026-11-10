"""Meta Ads CSV parser."""

from __future__ import annotations

import csv
from pathlib import Path

from app.ingestion.types import RawDeliveryRow

REQUIRED_HEADERS = ["campaign_name", "date", "spend_usd", "impressions", "clicks"]


def parse_meta_csv(path: Path) -> list[RawDeliveryRow]:
    """Parse a Meta delivery CSV into raw rows."""
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
                    platform="meta",
                    source_filename=path.name,
                    source_row_number=index,
                    campaign_raw=row.get("campaign_name"),
                    date_raw=row.get("date"),
                    spend_amount_raw=row.get("spend_usd"),
                    currency="USD",
                    impressions_raw=row.get("impressions"),
                    clicks_raw=row.get("clicks"),
                )
            )
        return rows
