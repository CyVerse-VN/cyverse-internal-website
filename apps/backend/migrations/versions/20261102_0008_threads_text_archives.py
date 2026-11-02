"""Replace Markdown archives with text archives without losing cleanup references.

Revision ID: 20261102_0008
Revises: 20261101_0007
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "20261102_0008"
down_revision: str | None = "20261101_0007"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    for previous, current in (
        ("markdown_status", "archive_status"),
        ("markdown_public_id", "archive_public_id"),
        ("markdown_uploaded_at", "archive_uploaded_at"),
    ):
        op.alter_column("threads_results", previous, new_column_name=current)
    op.add_column("threads_results", sa.Column("legacy_archive_public_id", sa.String(200)))
    # The worker uploads TXT before deleting the prior asset and keeps both IDs on failure.
    op.execute(
        "UPDATE threads_results SET archive_status = 'pending', next_storage_attempt_at = NULL"
    )


def downgrade() -> None:
    op.drop_column("threads_results", "legacy_archive_public_id")
    for current, previous in (
        ("archive_status", "markdown_status"),
        ("archive_public_id", "markdown_public_id"),
        ("archive_uploaded_at", "markdown_uploaded_at"),
    ):
        op.alter_column("threads_results", current, new_column_name=previous)
