"""Phase 4 quality_check_results table.

Revision ID: 20261110_0003
Revises: 20261109_0002
Create Date: 2026-11-10
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "20261110_0003"
down_revision: Union[str, None] = "20261109_0002"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "quality_check_results",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, nullable=False),
        sa.Column("delivery_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("ingestion_run_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("check_id", sa.String(length=64), nullable=False),
        sa.Column("severity", sa.String(length=16), nullable=False),
        sa.Column("outcome", sa.String(length=16), nullable=False),
        sa.Column("message", sa.Text(), nullable=False),
        sa.Column("affected_entities", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("details", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.ForeignKeyConstraint(["delivery_id"], ["deliveries.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["ingestion_run_id"], ["ingestion_runs.id"], ondelete="CASCADE"),
    )
    op.create_index(
        "ix_quality_check_results_delivery_id",
        "quality_check_results",
        ["delivery_id"],
    )
    op.create_index(
        "ix_quality_check_results_run_check",
        "quality_check_results",
        ["ingestion_run_id", "check_id"],
    )


def downgrade() -> None:
    op.drop_index("ix_quality_check_results_run_check", table_name="quality_check_results")
    op.drop_index("ix_quality_check_results_delivery_id", table_name="quality_check_results")
    op.drop_table("quality_check_results")
