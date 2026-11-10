"""Parameterized delivery check: project rejected-row reason codes into findings."""

from __future__ import annotations

from collections.abc import Callable, Mapping
from dataclasses import dataclass
from typing import Any

from app.quality.types import CadenceCheckContext, CheckFinding, DeliveryCheckContext, Severity


@dataclass(frozen=True)
class RejectedReasonCheck:
    """
    One check that fails when any rejected row matches a configured reason-code set.

    Replaces near-identical modules that only differed by reason codes and messages.
    """

    check_id: str
    severity: Severity
    reason_codes: frozenset[str]
    pass_message: str
    fail_message: str
    extra_row_fields: Callable[[Mapping[str, Any]], dict[str, Any]] | None = None

    def run(self, context: DeliveryCheckContext | CadenceCheckContext) -> list[CheckFinding]:
        if not isinstance(context, DeliveryCheckContext):
            return []

        affected: list[dict[str, Any]] = []
        for item in context.rejected:
            if item.reason_code not in self.reason_codes:
                continue
            row: dict[str, Any] = {
                "source_row_number": item.source_row_number,
                "reason_code": item.reason_code,
                "message": item.message,
            }
            if self.extra_row_fields is not None:
                row.update(self.extra_row_fields(item.raw_payload or {}))
            affected.append(row)

        entities: dict[str, Any] = {
            "platform": context.platform,
            "source_filename": context.authoritative_filename,
        }
        if not affected:
            return [
                CheckFinding(
                    check_id=self.check_id,
                    severity="info",
                    outcome="pass",
                    message=self.pass_message,
                    affected_entities=entities,
                )
            ]

        fail_entities = dict(entities)
        fail_entities["week_start"] = context.week_start.isoformat()
        fail_entities["rows"] = affected
        return [
            CheckFinding(
                check_id=self.check_id,
                severity=self.severity,
                outcome="fail",
                message=self.fail_message.format(count=len(affected)),
                affected_entities=fail_entities,
            )
        ]
