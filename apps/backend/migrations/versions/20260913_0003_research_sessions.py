"""Add durable AI research sessions and final papers.

Revision ID: 20260913_0003
Revises: 20260912_0002
Create Date: 2026-09-13
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "20260913_0003"
down_revision: str | None = "20260912_0002"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "tool_runs",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("owner_id", sa.Uuid(), nullable=False),
        sa.Column("tool_name", sa.String(length=64), nullable=False),
        sa.Column("status", sa.String(length=32), server_default="queued", nullable=False),
        sa.Column("current_stage", sa.String(length=32), server_default="queued", nullable=False),
        sa.Column("progress", sa.Float(), server_default="0", nullable=False),
        sa.Column("idempotency_key", sa.String(length=64), nullable=True),
        sa.Column("cancel_requested", sa.Boolean(), server_default=sa.false(), nullable=False),
        sa.Column("attempt_count", sa.Integer(), server_default="0", nullable=False),
        sa.Column("worker_id", sa.String(length=100), nullable=True),
        sa.Column("heartbeat_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("error_code", sa.String(length=64), nullable=True),
        sa.Column("error_message", sa.Text(), nullable=True),
        sa.Column(
            "details", postgresql.JSONB(astext_type=sa.Text()), server_default="{}", nullable=False
        ),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(["owner_id"], ["users.id"], ondelete="RESTRICT"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("owner_id", "idempotency_key", name="uq_tool_runs_idempotency"),
    )
    op.create_index("ix_tool_runs_owner_id", "tool_runs", ["owner_id"])
    op.create_index("ix_tool_runs_queue", "tool_runs", ["tool_name", "status", "created_at"])

    op.create_table(
        "tool_run_events",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("run_id", sa.Uuid(), nullable=False),
        sa.Column("sequence", sa.Integer(), nullable=False),
        sa.Column("stage", sa.String(length=32), nullable=False),
        sa.Column("status", sa.String(length=20), nullable=False),
        sa.Column("message", sa.String(length=240), nullable=False),
        sa.Column("progress", sa.Float(), nullable=False),
        sa.Column(
            "metadata", postgresql.JSONB(astext_type=sa.Text()), server_default="{}", nullable=False
        ),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(["run_id"], ["tool_runs.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("run_id", "sequence", name="uq_tool_run_events_seq"),
    )
    op.create_index("ix_tool_run_events_run_id", "tool_run_events", ["run_id"])

    op.create_table(
        "research_sessions",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("run_id", sa.Uuid(), nullable=False),
        sa.Column("query", sa.Text(), nullable=False),
        sa.Column("title", sa.String(length=120), nullable=False),
        sa.Column("visibility", sa.String(length=16), server_default="public", nullable=False),
        sa.Column(
            "effective_settings",
            postgresql.JSONB(astext_type=sa.Text()),
            server_default="{}",
            nullable=False,
        ),
        sa.Column("pipeline_version", sa.String(length=20), server_default="3.0.0", nullable=False),
        sa.Column(
            "warnings", postgresql.JSONB(astext_type=sa.Text()), server_default="[]", nullable=False
        ),
        sa.Column(
            "result_stats",
            postgresql.JSONB(astext_type=sa.Text()),
            server_default="{}",
            nullable=False,
        ),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(["run_id"], ["tool_runs.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("run_id"),
    )
    op.create_index(
        "ix_research_sessions_visibility_created",
        "research_sessions",
        ["visibility", "created_at"],
    )

    op.create_table(
        "research_papers",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("session_id", sa.Uuid(), nullable=False),
        sa.Column("rank", sa.Integer(), nullable=False),
        sa.Column("relevance_score", sa.Float(), nullable=False),
        sa.Column("read_priority", sa.String(length=16), nullable=False),
        sa.Column("dedup_key", sa.String(length=512), nullable=False),
        sa.Column("title", sa.String(length=1000), nullable=False),
        sa.Column("authors", postgresql.JSONB(astext_type=sa.Text()), server_default="[]", nullable=False),
        sa.Column("year", sa.Integer(), nullable=True),
        sa.Column("published_at", sa.Date(), nullable=True),
        sa.Column("venue", sa.String(length=500), nullable=True),
        sa.Column("doi", sa.String(length=300), nullable=True),
        sa.Column("arxiv_id", sa.String(length=100), nullable=True),
        sa.Column("sources", postgresql.JSONB(astext_type=sa.Text()), server_default="[]", nullable=False),
        sa.Column("paper_type", sa.String(length=32), nullable=False),
        sa.Column("fields", postgresql.JSONB(astext_type=sa.Text()), server_default="[]", nullable=False),
        sa.Column("citation_count", sa.Integer(), nullable=True),
        sa.Column("is_open_access", sa.Boolean(), nullable=True),
        sa.Column("pdf_url", sa.String(length=2048), nullable=True),
        sa.Column("landing_url", sa.String(length=2048), nullable=True),
        sa.Column("summary_vi", sa.Text(), nullable=False),
        sa.Column("why_read_vi", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.ForeignKeyConstraint(["session_id"], ["research_sessions.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("session_id", "dedup_key", name="uq_research_papers_dedup"),
        sa.UniqueConstraint("session_id", "rank", name="uq_research_papers_rank"),
    )
    op.create_index("ix_research_papers_session_id", "research_papers", ["session_id"])


def downgrade() -> None:
    op.drop_table("research_papers")
    op.drop_table("research_sessions")
    op.drop_table("tool_run_events")
    op.drop_table("tool_runs")
