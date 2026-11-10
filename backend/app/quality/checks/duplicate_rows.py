"""Row-level check: duplicate logical keys inside a delivery file."""

from __future__ import annotations

from collections import defaultdict

from app.quality.types import CadenceCheckContext, CheckFinding, DeliveryCheckContext


class DuplicateRowsCheck:
    check_id = "duplicate_rows"

    def run(self, context: DeliveryCheckContext | CadenceCheckContext) -> list[CheckFinding]:
        if not isinstance(context, DeliveryCheckContext):
            return []

        # Approximate logical key using raw campaign strip + raw date string.
        groups: dict[tuple[str, str], list[int]] = defaultdict(list)
        for row in context.raw_rows:
            campaign = str(row.campaign_raw).strip() if row.campaign_raw is not None else ""
            date_key = str(row.date_raw)
            groups[(campaign, date_key)].append(row.source_row_number)

        duplicates = {key: rows for key, rows in groups.items() if len(rows) > 1}
        if not duplicates:
            return [
                CheckFinding(
                    check_id=self.check_id,
                    severity="info",
                    outcome="pass",
                    message="No duplicate logical rows detected",
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
                message=f"Found {len(duplicates)} duplicate logical key group(s)",
                affected_entities={
                    "platform": context.platform,
                    "source_filename": context.authoritative_filename,
                    "duplicate_groups": [
                        {
                            "campaign": campaign,
                            "date_raw": date_raw,
                            "row_numbers": row_numbers,
                        }
                        for (campaign, date_raw), row_numbers in duplicates.items()
                    ],
                },
            )
        ]
