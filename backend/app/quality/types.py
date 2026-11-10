"""Quality-check contract types (ADR-003)."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date
from typing import Any, Literal, Optional, Protocol

from app.ingestion.types import DeliveryFileRef, NormalizedMetric, RawDeliveryRow, RejectedMetric

Severity = Literal["error", "warn", "info"]
Outcome = Literal["pass", "fail"]


@dataclass(frozen=True)
class CheckFinding:
    """One structured finding produced by a quality check."""

    check_id: str
    severity: Severity
    outcome: Outcome
    message: str
    affected_entities: dict[str, Any] = field(default_factory=dict)
    details: dict[str, Any] = field(default_factory=dict)


@dataclass
class DeliveryCheckContext:
    """Inputs available to per-delivery quality checks."""

    platform: str
    week_start: date
    file_refs: list[DeliveryFileRef]
    authoritative_filename: Optional[str]
    content_checksum: Optional[str]
    raw_rows: list[RawDeliveryRow]
    accepted: list[NormalizedMetric]
    rejected: list[RejectedMetric]
    delivery_id: Optional[str] = None


@dataclass
class CadenceCheckContext:
    """Inputs available to cross-delivery cadence checks."""

    expected_platforms: tuple[str, ...]
    expected_week_starts: list[date]
    present_keys: set[tuple[str, date]]
    discovered_files: list[DeliveryFileRef]


class QualityCheck(Protocol):
    """Independent quality check contract."""

    check_id: str

    def run(self, context: DeliveryCheckContext | CadenceCheckContext) -> list[CheckFinding]:
        """Execute the check and return zero or more findings."""
