"""Phase 3 domain tables for deliveries and metrics.

Revision ID: 20261109_0002
Revises: 20261109_0001
Create Date: 2026-11-09
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "20261109_0002"
down_revision: Union[str, None] = "20261109_0001"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "ingestion_runs",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, nullable=False),
        sa.Column(
            "started_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column("finished_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("status", sa.String(length=32), nullable=False),
        sa.Column("summary", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
    )

    op.create_table(
        "deliveries",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, nullable=False),
        sa.Column("platform", sa.String(length=32), nullable=False),
        sa.Column("week_start", sa.Date(), nullable=False),
        sa.Column("source_filename", sa.String(length=255), nullable=True),
        sa.Column("content_checksum", sa.String(length=64), nullable=True),
        sa.Column("health", sa.String(length=16), nullable=False),
        sa.Column("last_run_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column(
            "ingested_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(["last_run_id"], ["ingestion_runs.id"], ondelete="SET NULL"),
        sa.UniqueConstraint("platform", "week_start", name="uq_deliveries_platform_week"),
    )
    op.create_index("ix_deliveries_health", "deliveries", ["health"])

    op.create_table(
        "metric_rows",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, nullable=False),
        sa.Column("delivery_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("platform", sa.String(length=32), nullable=False),
        sa.Column("campaign", sa.String(length=255), nullable=False),
        sa.Column("campaign_raw", sa.String(length=255), nullable=False),
        sa.Column("date", sa.Date(), nullable=False),
        sa.Column("spend_usd", sa.Numeric(18, 6), nullable=False),
        sa.Column("impressions", sa.Integer(), nullable=False),
        sa.Column("clicks", sa.Integer(), nullable=False),
        sa.Column("source_filename", sa.String(length=255), nullable=False),
        sa.ForeignKeyConstraint(["delivery_id"], ["deliveries.id"], ondelete="CASCADE"),
        sa.UniqueConstraint(
            "platform", "campaign", "date", name="uq_metric_rows_platform_campaign_date"
        ),
    )
    op.create_index("ix_metric_rows_platform_date", "metric_rows", ["platform", "date"])
    op.create_index("ix_metric_rows_date", "metric_rows", ["date"])
    op.create_index("ix_metric_rows_campaign", "metric_rows", ["campaign"])

    op.create_table(
        "rejected_rows",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, nullable=False),
        sa.Column("delivery_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("platform", sa.String(length=32), nullable=False),
        sa.Column("source_filename", sa.String(length=255), nullable=False),
        sa.Column("source_row_number", sa.Integer(), nullable=True),
        sa.Column("raw_payload", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("reason_code", sa.String(length=64), nullable=False),
        sa.Column("message", sa.Text(), nullable=False),
        sa.ForeignKeyConstraint(["delivery_id"], ["deliveries.id"], ondelete="CASCADE"),
    )
    op.create_index("ix_rejected_rows_delivery_id", "rejected_rows", ["delivery_id"])


def downgrade() -> None:
    op.drop_index("ix_rejected_rows_delivery_id", table_name="rejected_rows")
    op.drop_table("rejected_rows")
    op.drop_index("ix_metric_rows_campaign", table_name="metric_rows")
    op.drop_index("ix_metric_rows_date", table_name="metric_rows")
    op.drop_index("ix_metric_rows_platform_date", table_name="metric_rows")
    op.drop_table("metric_rows")
    op.drop_index("ix_deliveries_health", table_name="deliveries")
    op.drop_table("deliveries")
    op.drop_table("ingestion_runs")
