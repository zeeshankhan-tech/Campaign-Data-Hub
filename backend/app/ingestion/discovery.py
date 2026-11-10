"""Discover delivery files and map them to platform/week keys."""

from __future__ import annotations

import re
from datetime import date, datetime
from pathlib import Path

from app.ingestion.types import DeliveryFileRef

_FILE_RE = re.compile(
    r"^(?P<platform>meta_ads|google_ads|linkedin_ads)_"
    r"(?P<week>\d{4}-\d{2}-\d{2})"
    r"(?P<resend>_resend)?"
    r"\.(?P<ext>csv|json)$"
)

_PLATFORM_MAP = {
    "meta_ads": "meta",
    "google_ads": "google",
    "linkedin_ads": "linkedin",
}


def discover_delivery_files(deliveries_dir: Path) -> list[DeliveryFileRef]:
    """Return sorted delivery file refs under the deliveries directory."""
    if not deliveries_dir.is_dir():
        raise FileNotFoundError(f"deliveries directory not found: {deliveries_dir}")

    refs: list[DeliveryFileRef] = []
    for path in sorted(deliveries_dir.iterdir()):
        if not path.is_file() or path.name.startswith("."):
            continue
        match = _FILE_RE.match(path.name)
        if not match:
            continue
        platform = _PLATFORM_MAP[match.group("platform")]
        week_start = datetime.strptime(match.group("week"), "%Y-%m-%d").date()
        refs.append(
            DeliveryFileRef(
                path=str(path),
                filename=path.name,
                platform=platform,
                week_start=week_start,
                is_resend=bool(match.group("resend")),
            )
        )
    return refs


def expected_week_starts() -> list[date]:
    """Assessment expected weekly cadence week-start dates."""
    return [
        date(2026, 6, 1),
        date(2026, 6, 8),
        date(2026, 6, 15),
        date(2026, 6, 22),
        date(2026, 6, 29),
    ]
