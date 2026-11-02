"""Add Threads sharing, incremental persistence, and durable artifact cleanup.

Revision ID: 20261101_0007
Revises: 20261101_0006
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "20261101_0007"
down_revision: str | None = "20261101_0006"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    # Existing sessions retain their owner/admin-only access until explicitly shared.
    op.add_column(
        "threads_results",
        sa.Column("visibility", sa.String(16), nullable=False, server_default="private"),
    )
    op.add_column(
        "threads_results",
        sa.Column("snapshot_ready", sa.Boolean(), nullable=False, server_default=sa.true()),
    )
    for name in ("post_count", "comment_count", "storage_attempt_count"):
        op.add_column(
            "threads_results", sa.Column(name, sa.Integer(), nullable=False, server_default="0")
        )
    op.add_column(
        "threads_results",
        sa.Column("markdown_status", sa.String(16), nullable=False, server_default="pending"),
    )
    op.add_column("threads_results", sa.Column("markdown_public_id", sa.String(200)))
    op.add_column("threads_results", sa.Column("markdown_uploaded_at", sa.DateTime(timezone=True)))
    op.add_column("threads_results", sa.Column("storage_error", sa.String(64)))
    op.add_column(
        "threads_results", sa.Column("next_storage_attempt_at", sa.DateTime(timezone=True))
    )
    op.add_column(
        "threads_results",
        sa.Column("deletion_requested", sa.Boolean(), nullable=False, server_default=sa.false()),
    )
    op.execute("""
        UPDATE threads_results SET
          post_count = (SELECT count(*) FROM threads_posts p
                        WHERE p.run_id = threads_results.run_id),
          comment_count = (SELECT count(*) FROM threads_comments c
                           JOIN threads_posts p ON p.id = c.post_record_id
                           WHERE p.run_id = threads_results.run_id)
    """)
    op.alter_column("threads_results", "visibility", server_default="public")
    op.alter_column("threads_results", "snapshot_ready", server_default=sa.false())
    op.create_index(
        "ix_threads_results_storage",
        "threads_results",
        ["deletion_requested", "next_storage_attempt_at"],
    )


def downgrade() -> None:
    op.drop_index("ix_threads_results_storage", table_name="threads_results")
    for name in (
        "deletion_requested",
        "storage_attempt_count",
        "next_storage_attempt_at",
        "storage_error",
        "markdown_uploaded_at",
        "markdown_public_id",
        "markdown_status",
        "comment_count",
        "post_count",
        "snapshot_ready",
        "visibility",
    ):
        op.drop_column("threads_results", name)
