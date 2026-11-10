"""Quality-check execution engine."""

from __future__ import annotations

from app.quality.types import (
    CadenceCheckContext,
    CheckFinding,
    DeliveryCheckContext,
    QualityCheck,
)


def run_checks(
    checks: list[QualityCheck],
    context: DeliveryCheckContext | CadenceCheckContext,
) -> list[CheckFinding]:
    """
    Run independent checks and collect findings.

    Each check is isolated: an unexpected exception becomes an error finding
    so one broken check cannot abort the rest of the quality pass.
    """
    findings: list[CheckFinding] = []
    for check in checks:
        try:
            findings.extend(check.run(context))
        except Exception as exc:  # noqa: BLE001
            findings.append(
                CheckFinding(
                    check_id=getattr(check, "check_id", "unknown_check"),
                    severity="error",
                    outcome="fail",
                    message=f"check crashed: {exc}",
                    details={"exception_type": type(exc).__name__},
                )
            )
    return findings
