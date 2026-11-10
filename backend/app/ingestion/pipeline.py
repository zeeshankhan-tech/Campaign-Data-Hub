"""Ingestion orchestration: discover → parse → normalize → quality → persist."""

from __future__ import annotations

import hashlib
import logging
from collections import defaultdict
from dataclasses import dataclass, field
from datetime import date
from pathlib import Path
from typing import Any, Optional
from uuid import UUID

from sqlalchemy.orm import Session

from app.db.models import Delivery, IngestionRun
from app.ingestion.discovery import discover_delivery_files, expected_week_starts
from app.ingestion.fx import load_exchange_rates
from app.ingestion.identity import delivery_key
from app.ingestion.normalize import normalize_rows
from app.ingestion.parsers import parse_delivery_file
from app.ingestion.types import DeliveryFileRef, NormalizedMetric, RejectedMetric
from app.quality import CADENCE_CHECKS, DELIVERY_CHECKS, derive_health, run_checks
from app.quality.findings import synthetic_finding
from app.quality.types import CadenceCheckContext, CheckFinding, DeliveryCheckContext
from app.repositories import ingestion as ingestion_repo

logger = logging.getLogger(__name__)

PLATFORMS = ("meta", "google", "linkedin")


@dataclass
class DeliveryProcessResult:
    platform: str
    week_start: date
    source_filename: str | None
    accepted_count: int = 0
    rejected_count: int = 0
    health: str = "unknown"
    error: str | None = None
    failing_checks: list[str] = field(default_factory=list)


@dataclass
class IngestionResult:
    run_id: str
    status: str
    deliveries: list[DeliveryProcessResult] = field(default_factory=list)
    accepted_total: int = 0
    rejected_total: int = 0
    summary: dict[str, Any] = field(default_factory=dict)


def _checksum(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _failing_check_ids(findings: list[CheckFinding]) -> list[str]:
    return sorted({f.check_id for f in findings if f.outcome == "fail"})


def persist_delivery_snapshot(
    session: Session,
    *,
    platform: str,
    week_start: date,
    source_filename: Optional[str],
    content_checksum: Optional[str],
    health: str,
    run_id: UUID,
    accepted: list[NormalizedMetric],
    rejected: list[RejectedMetric],
    findings: list[CheckFinding],
) -> Delivery:
    """
    Authoritatively replace one delivery's rows + findings.

    Shared by success, file-failure, and cadence-missing paths so replace
    semantics live in one place.
    """
    delivery = ingestion_repo.upsert_delivery(
        session,
        platform=platform,
        week_start=week_start,
        source_filename=source_filename,
        content_checksum=content_checksum,
        health=health,
        run_id=run_id,
    )
    ingestion_repo.replace_delivery_rows(
        session,
        delivery,
        accepted=accepted,
        rejected=rejected,
    )
    ingestion_repo.replace_quality_findings(
        session,
        delivery=delivery,
        run_id=run_id,
        findings=findings,
    )
    session.commit()
    return delivery


def run_ingestion(
    session: Session,
    *,
    data_dir: Path,
) -> IngestionResult:
    """
    Ingest all delivery files under `data_dir/deliveries`.

    Continues across file/row failures (error isolation). Quality checks run
    per delivery and once for cadence after file processing.
    """
    deliveries_dir = data_dir / "deliveries"
    rates_path = data_dir / "exchange_rates.json"
    fx_rates = load_exchange_rates(rates_path)
    file_refs = discover_delivery_files(deliveries_dir)

    run = ingestion_repo.create_ingestion_run(session)
    session.commit()

    results: list[DeliveryProcessResult] = []
    accepted_total = 0
    rejected_total = 0
    run_status = "completed"

    grouped: dict[tuple[str, date], list[DeliveryFileRef]] = defaultdict(list)
    for ref in file_refs:
        grouped[delivery_key(ref.platform, ref.week_start)].append(ref)

    try:
        for (platform, week_start), refs in sorted(grouped.items()):
            refs_sorted = sorted(refs, key=lambda r: (r.is_resend, r.filename))
            authoritative = refs_sorted[-1]
            delivery_result = DeliveryProcessResult(
                platform=platform,
                week_start=week_start,
                source_filename=authoritative.filename,
            )
            try:
                path = Path(authoritative.path)
                checksum = _checksum(path)
                raw_rows = parse_delivery_file(authoritative)
                accepted, rejected = normalize_rows(raw_rows, fx_rates)

                check_context = DeliveryCheckContext(
                    platform=platform,
                    week_start=week_start,
                    file_refs=refs_sorted,
                    authoritative_filename=authoritative.filename,
                    content_checksum=checksum,
                    raw_rows=raw_rows,
                    accepted=accepted,
                    rejected=rejected,
                )
                findings = run_checks(DELIVERY_CHECKS, check_context)
                health = derive_health(findings)

                persist_delivery_snapshot(
                    session,
                    platform=platform,
                    week_start=week_start,
                    source_filename=authoritative.filename,
                    content_checksum=checksum,
                    health=health,
                    run_id=run.id,
                    accepted=accepted,
                    rejected=rejected,
                    findings=findings,
                )

                delivery_result.accepted_count = len(accepted)
                delivery_result.rejected_count = len(rejected)
                delivery_result.health = health
                delivery_result.failing_checks = _failing_check_ids(findings)
                accepted_total += len(accepted)
                rejected_total += len(rejected)
            except Exception as exc:  # noqa: BLE001 — isolate per delivery file
                logger.exception("Failed processing delivery %s %s", platform, week_start)
                session.rollback()
                delivery_result.error = str(exc)
                delivery_result.health = "fail"
                try:
                    failure_finding = synthetic_finding(
                        check_id="file_processing_error",
                        message=str(exc),
                        affected_entities={
                            "platform": platform,
                            "week_start": week_start.isoformat(),
                            "source_filename": authoritative.filename,
                        },
                    )
                    persist_delivery_snapshot(
                        session,
                        platform=platform,
                        week_start=week_start,
                        source_filename=authoritative.filename,
                        content_checksum=None,
                        health="fail",
                        run_id=run.id,
                        accepted=[],
                        rejected=[
                            RejectedMetric(
                                platform=platform,
                                source_filename=authoritative.filename,
                                source_row_number=0,
                                reason_code="file_processing_error",
                                message=str(exc),
                                raw_payload={},
                            )
                        ],
                        findings=[failure_finding],
                    )
                    delivery_result.failing_checks = ["file_processing_error"]
                except Exception:  # noqa: BLE001
                    session.rollback()
                    logger.exception(
                        "Could not persist failure marker for %s %s", platform, week_start
                    )
            results.append(delivery_result)

        # Cadence checks for missing expected deliveries.
        present = {delivery_key(r.platform, r.week_start) for r in results}
        cadence_context = CadenceCheckContext(
            expected_platforms=PLATFORMS,
            expected_week_starts=expected_week_starts(),
            present_keys=present,
            discovered_files=file_refs,
        )
        cadence_findings = run_checks(CADENCE_CHECKS, cadence_context)
        findings_by_key: dict[tuple[str, date], list[CheckFinding]] = defaultdict(list)
        for finding in cadence_findings:
            if finding.outcome != "fail":
                continue
            platform = finding.affected_entities.get("platform")
            week_raw = finding.affected_entities.get("week_start")
            if not platform or not week_raw:
                continue
            week_start = date.fromisoformat(week_raw)
            findings_by_key[delivery_key(platform, week_start)].append(finding)

        for (platform, week_start), findings in sorted(findings_by_key.items()):
            marker = DeliveryProcessResult(
                platform=platform,
                week_start=week_start,
                source_filename=None,
                health=derive_health(findings),
                error="missing_expected_delivery",
                failing_checks=_failing_check_ids(findings),
            )
            persist_delivery_snapshot(
                session,
                platform=platform,
                week_start=week_start,
                source_filename=None,
                content_checksum=None,
                health=marker.health,
                run_id=run.id,
                accepted=[],
                rejected=[
                    RejectedMetric(
                        platform=platform,
                        source_filename="",
                        source_row_number=0,
                        reason_code="missing_expected_delivery",
                        message=findings[0].message,
                        raw_payload={},
                    )
                ],
                findings=findings,
            )
            results.append(marker)

    except Exception as exc:  # noqa: BLE001
        logger.exception("Ingestion run failed")
        run_status = "failed"
        session.rollback()
        summary = {
            "error": str(exc),
            "accepted_total": accepted_total,
            "rejected_total": rejected_total,
            "deliveries": [r.__dict__ for r in results],
        }
        run_entity = session.get(IngestionRun, run.id)
        assert run_entity is not None
        ingestion_repo.finish_ingestion_run(
            session, run_entity, status=run_status, summary=summary
        )
        session.commit()
        return IngestionResult(
            run_id=str(run.id),
            status=run_status,
            deliveries=results,
            accepted_total=accepted_total,
            rejected_total=rejected_total,
            summary=summary,
        )

    validation_failures = sum(1 for r in results if r.rejected_count > 0 and r.error is None)
    infrastructure_failures = sum(1 for r in results if r.error not in (None, "missing_expected_delivery"))
    cadence_failures = sum(1 for r in results if r.error == "missing_expected_delivery")

    summary = {
        "accepted_total": accepted_total,
        "rejected_total": rejected_total,
        "delivery_count": len(results),
        "registered_checks": [c.check_id for c in DELIVERY_CHECKS + CADENCE_CHECKS],
        "failure_classes": {
            "validation_or_quality": validation_failures,
            "infrastructure_or_file": infrastructure_failures,
            "missing_expected_delivery": cadence_failures,
        },
        "deliveries": [
            {
                "platform": r.platform,
                "week_start": r.week_start.isoformat(),
                "source_filename": r.source_filename,
                "accepted_count": r.accepted_count,
                "rejected_count": r.rejected_count,
                "health": r.health,
                "error": r.error,
                "failing_checks": r.failing_checks,
            }
            for r in results
        ],
    }
    run_entity = session.get(IngestionRun, run.id)
    assert run_entity is not None
    ingestion_repo.finish_ingestion_run(session, run_entity, status=run_status, summary=summary)
    session.commit()

    return IngestionResult(
        run_id=str(run.id),
        status=run_status,
        deliveries=results,
        accepted_total=accepted_total,
        rejected_total=rejected_total,
        summary=summary,
    )
