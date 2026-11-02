"""Persist Threads account sessions for serverless and cloud restarts.

Revision ID: 20261103_0009
Revises: 20261102_0008
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "20261103_0009"
down_revision: str | None = "20261102_0008"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "threads_account_sessions",
        sa.Column("account_id", sa.String(64), primary_key=True),
        sa.Column("session_data", sa.JSON(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
    )


def downgrade() -> None:
    op.drop_table("threads_account_sessions")
