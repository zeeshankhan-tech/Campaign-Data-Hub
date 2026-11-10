"""Row-level check: trailing whitespace and case-variant campaign names."""

from __future__ import annotations

from collections import defaultdict

from app.quality.types import CadenceCheckContext, CheckFinding, DeliveryCheckContext


class CampaignNameHygieneCheck:
    check_id = "campaign_name_hygiene"

    def run(self, context: DeliveryCheckContext | CadenceCheckContext) -> list[CheckFinding]:
        if not isinstance(context, DeliveryCheckContext):
            return []

        whitespace_rows: list[dict] = []
        case_groups: dict[str, set[str]] = defaultdict(set)

        for row in context.raw_rows:
            if row.campaign_raw is None:
                continue
            raw = str(row.campaign_raw)
            stripped = raw.strip()
            if raw != stripped:
                whitespace_rows.append(
                    {
                        "source_row_number": row.source_row_number,
                        "campaign_raw": raw,
                    }
                )
            if stripped:
                case_groups[stripped.casefold()].add(stripped)

        case_collisions = {
            key: sorted(values)
            for key, values in case_groups.items()
            if len(values) > 1
        }

        if not whitespace_rows and not case_collisions:
            return [
                CheckFinding(
                    check_id=self.check_id,
                    severity="info",
                    outcome="pass",
                    message="Campaign names look consistent",
                    affected_entities={
                        "platform": context.platform,
                        "source_filename": context.authoritative_filename,
                    },
                )
            ]

        return [
            CheckFinding(
                check_id=self.check_id,
                severity="warn",
                outcome="fail",
                message="Campaign name hygiene issues detected",
                affected_entities={
                    "platform": context.platform,
                    "source_filename": context.authoritative_filename,
                    "trailing_whitespace_rows": whitespace_rows,
                    "case_variant_groups": case_collisions,
                },
            )
        ]
