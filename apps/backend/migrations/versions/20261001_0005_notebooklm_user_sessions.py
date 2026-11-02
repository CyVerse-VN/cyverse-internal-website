"""Add user-selected NotebookLM accounts and encrypted import sessions.

Revision ID: 20261001_0005
Revises: 20261001_0004
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "20261001_0005"
down_revision: str | None = "20261001_0004"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column("users", sa.Column("notebooklm_email", sa.String(length=320), nullable=True))
    op.add_column("notebooklm_imports", sa.Column("account_email", sa.String(length=320), nullable=True))
    op.add_column("notebooklm_imports", sa.Column("session_ciphertext", sa.Text(), nullable=True))


def downgrade() -> None:
    op.drop_column("notebooklm_imports", "session_ciphertext")
    op.drop_column("notebooklm_imports", "account_email")
    op.drop_column("users", "notebooklm_email")
