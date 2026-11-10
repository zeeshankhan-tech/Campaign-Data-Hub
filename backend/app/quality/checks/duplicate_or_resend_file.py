"""File-level check: resend or multiple files for the same delivery week."""

from __future__ import annotations

from app.quality.types import CadenceCheckContext, CheckFinding, DeliveryCheckContext


class DuplicateOrResendFileCheck:
    check_id = "duplicate_or_resend_file"

    def run(self, context: DeliveryCheckContext | CadenceCheckContext) -> list[CheckFinding]:
        if not isinstance(context, DeliveryCheckContext):
            return []

        filenames = [ref.filename for ref in context.file_refs]
        resend_files = [ref.filename for ref in context.file_refs if ref.is_resend]
        if len(context.file_refs) <= 1 and not resend_files:
            return [
                CheckFinding(
                    check_id=self.check_id,
                    severity="info",
                    outcome="pass",
                    message="No duplicate/resend files for this delivery",
                    affected_entities={
                        "platform": context.platform,
                        "week_start": context.week_start.isoformat(),
                    },
                )
            ]

        return [
            CheckFinding(
                check_id=self.check_id,
                severity="warn",
                outcome="fail",
                message=(
                    "Multiple files mapped to the same delivery "
                    f"(platform={context.platform}, week_start={context.week_start.isoformat()})"
                ),
                affected_entities={
                    "platform": context.platform,
                    "week_start": context.week_start.isoformat(),
                    "filenames": filenames,
                },
                details={
                    "resend_files": resend_files,
                    "authoritative_filename": context.authoritative_filename,
                    "content_checksum": context.content_checksum,
                },
            )
        ]
