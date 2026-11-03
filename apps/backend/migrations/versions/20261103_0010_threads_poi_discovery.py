"""Add tables for Threads Evidence-grounded POI Discovery.

Revision ID: 20261103_0010
Revises: 20261103_0009
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "20261103_0010"
down_revision: str | None = "20261103_0009"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "threads_poi_candidates",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column(
            "run_id",
            sa.Uuid(),
            sa.ForeignKey("threads_results.run_id", ondelete="CASCADE"),
            nullable=False,
            index=True,
        ),
        sa.Column("canonical_name", sa.String(256), nullable=False, index=True),
        sa.Column("category", sa.String(128)),
        sa.Column("area", sa.String(256)),
        sa.Column("address", sa.String(512)),
        sa.Column("verification_status", sa.String(32), default="candidate", nullable=False),
        sa.Column("metadata_json", sa.JSON(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
    )

    op.create_table(
        "threads_poi_mentions",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column(
            "candidate_id",
            sa.Uuid(),
            sa.ForeignKey("threads_poi_candidates.id", ondelete="CASCADE"),
            index=True,
        ),
        sa.Column(
            "run_id",
            sa.Uuid(),
            sa.ForeignKey("threads_results.run_id", ondelete="CASCADE"),
            nullable=False,
            index=True,
        ),
        sa.Column("post_id", sa.String(128), nullable=False),
        sa.Column("comment_id", sa.String(128)),
        sa.Column("name_text", sa.String(256), nullable=False),
        sa.Column("category_text", sa.String(128)),
        sa.Column("area_text", sa.String(256)),
        sa.Column("address_text", sa.String(512)),
        sa.Column("evidence_text", sa.String(2000), nullable=False),
        sa.Column("start_offset", sa.Integer()),
        sa.Column("end_offset", sa.Integer()),
        sa.Column("context_incomplete", sa.Boolean(), default=False, nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    )

    op.create_table(
        "threads_poi_claims",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column(
            "mention_id",
            sa.Uuid(),
            sa.ForeignKey("threads_poi_mentions.id", ondelete="CASCADE"),
            nullable=False,
            index=True,
        ),
        sa.Column(
            "run_id",
            sa.Uuid(),
            sa.ForeignKey("threads_results.run_id", ondelete="CASCADE"),
            nullable=False,
            index=True,
        ),
        sa.Column("claim_type", sa.String(64), nullable=False),
        sa.Column("value", sa.String(512), nullable=False),
        sa.Column("evidence_text", sa.String(2000), nullable=False),
        sa.Column("source_post_id", sa.String(128), nullable=False),
        sa.Column("source_comment_id", sa.String(128)),
        sa.Column("sentiment", sa.String(32), default="unknown", nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    )


def downgrade() -> None:
    op.drop_table("threads_poi_claims")
    op.drop_table("threads_poi_mentions")
    op.drop_table("threads_poi_candidates")
