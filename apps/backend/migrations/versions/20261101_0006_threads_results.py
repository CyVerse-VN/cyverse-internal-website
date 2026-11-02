"""Store Threads result, post, and comment snapshots.

Revision ID: 20261101_0006
Revises: 20261001_0005
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "20261101_0006"
down_revision: str | None = "20261001_0005"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "threads_results",
        sa.Column("run_id", sa.Uuid(), nullable=False),
        sa.Column("summary", postgresql.JSONB(), nullable=False),
        sa.ForeignKeyConstraint(["run_id"], ["tool_runs.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("run_id"),
    )
    op.create_table(
        "threads_posts",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("run_id", sa.Uuid(), nullable=False),
        sa.Column("post_id", sa.String(128), nullable=False),
        sa.Column("position", sa.Integer(), nullable=False),
        sa.Column("data", postgresql.JSONB(), nullable=False),
        sa.ForeignKeyConstraint(["run_id"], ["threads_results.run_id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("run_id", "post_id", name="uq_threads_posts_source"),
        sa.UniqueConstraint("run_id", "position", name="uq_threads_posts_position"),
    )
    op.create_index("ix_threads_posts_run_id", "threads_posts", ["run_id"])
    op.create_table(
        "threads_comments",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("post_record_id", sa.Uuid(), nullable=False),
        sa.Column("comment_id", sa.String(128), nullable=False),
        sa.Column("parent_comment_id", sa.String(128), nullable=True),
        sa.Column("position", sa.Integer(), nullable=False),
        sa.Column("data", postgresql.JSONB(), nullable=False),
        sa.ForeignKeyConstraint(["post_record_id"], ["threads_posts.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("post_record_id", "comment_id", name="uq_threads_comments_source"),
        sa.UniqueConstraint("post_record_id", "position", name="uq_threads_comments_position"),
    )
    op.create_index("ix_threads_comments_post_record_id", "threads_comments", ["post_record_id"])


def downgrade() -> None:
    op.drop_table("threads_comments")
    op.drop_table("threads_posts")
    op.drop_table("threads_results")
