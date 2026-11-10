"""Derive delivery health from quality findings (ADR-002)."""

from __future__ import annotations

from app.quality.types import CheckFinding


def derive_health(findings: list[CheckFinding]) -> str:
    """
    Map findings to pass/warn/fail.

    - fail: any finding with severity=error and outcome=fail
    - warn: else any finding with severity=warn and outcome=fail
    - pass: otherwise
    """
    has_error = any(f.outcome == "fail" and f.severity == "error" for f in findings)
    if has_error:
        return "fail"
    has_warn = any(f.outcome == "fail" and f.severity == "warn" for f in findings)
    if has_warn:
        return "warn"
    return "pass"
