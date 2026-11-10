"""Shared helpers for constructing quality findings."""

from __future__ import annotations

from typing import Any, Optional

from app.quality.types import CheckFinding, Outcome, Severity


def synthetic_finding(
    *,
    check_id: str,
    message: str,
    severity: Severity = "error",
    outcome: Outcome = "fail",
    affected_entities: Optional[dict[str, Any]] = None,
    details: Optional[dict[str, Any]] = None,
) -> CheckFinding:
    """Build a finding outside a registered check module (e.g. file processing errors)."""
    return CheckFinding(
        check_id=check_id,
        severity=severity,
        outcome=outcome,
        message=message,
        affected_entities=affected_entities or {},
        details=details or {},
    )
