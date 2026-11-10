"""Cadence check: expected weekly delivery file is absent."""

from __future__ import annotations

from app.quality.types import CadenceCheckContext, CheckFinding, DeliveryCheckContext


class MissingExpectedDeliveryCheck:
    check_id = "missing_expected_delivery"

    def run(self, context: DeliveryCheckContext | CadenceCheckContext) -> list[CheckFinding]:
        if not isinstance(context, CadenceCheckContext):
            return []

        findings: list[CheckFinding] = []
        for platform in context.expected_platforms:
            for week_start in context.expected_week_starts:
                key = (platform, week_start)
                if key in context.present_keys:
                    continue
                findings.append(
                    CheckFinding(
                        check_id=self.check_id,
                        severity="error",
                        outcome="fail",
                        message=(
                            f"Expected weekly delivery missing for platform={platform} "
                            f"week_start={week_start.isoformat()}"
                        ),
                        affected_entities={
                            "platform": platform,
                            "week_start": week_start.isoformat(),
                        },
                    )
                )
        return findings
