"""Phase 2 baseline — no domain tables yet.

Revision ID: 20261109_0001
Revises:
Create Date: 2026-11-09
"""

from typing import Sequence, Union

revision: str = "20261109_0001"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """No schema changes in Phase 2; establishes Alembic history."""
    pass


def downgrade() -> None:
    """No schema changes to reverse."""
    pass
