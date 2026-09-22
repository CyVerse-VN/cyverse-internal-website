"""Replace database sessions with stateless signed tokens.

Revision ID: 20260912_0002
Revises: 20260910_0001
Create Date: 2026-09-12
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "20260912_0002"
down_revision: str | None = "20260910_0001"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    # This migration tolerates a manually removed auth_sessions table and a
    # partially added token_version column so it can repair schema drift safely.
    op.execute("ALTER TABLE users ADD COLUMN IF NOT EXISTS token_version INTEGER")
    op.execute("UPDATE users SET token_version = 0 WHERE token_version IS NULL")
    op.execute("ALTER TABLE users ALTER COLUMN token_version SET DEFAULT 0")
    op.execute("ALTER TABLE users ALTER COLUMN token_version SET NOT NULL")
    op.execute("DROP TABLE IF EXISTS auth_sessions")


def downgrade() -> None:
    op.create_table(
        "auth_sessions",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("user_id", sa.Uuid(), nullable=False),
        sa.Column("token_hash", sa.String(length=64), nullable=False),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("revoked_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.Column(
            "updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_auth_sessions_token_hash", "auth_sessions", ["token_hash"], unique=True)
    op.create_index("ix_auth_sessions_user_id", "auth_sessions", ["user_id"], unique=False)
    op.drop_column("users", "token_version")
