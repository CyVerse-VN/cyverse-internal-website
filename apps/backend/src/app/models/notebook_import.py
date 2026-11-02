from __future__ import annotations

from uuid import UUID, uuid4

from sqlalchemy import ForeignKey, String, Text, Uuid
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base, TimestampMixin
from app.models.tool_run import JSON_TYPE, ToolRun


class NotebookImport(TimestampMixin, Base):
    __tablename__ = "notebooklm_imports"

    id: Mapped[UUID] = mapped_column(Uuid, primary_key=True, default=uuid4)
    run_id: Mapped[UUID] = mapped_column(
        ForeignKey("tool_runs.id", ondelete="CASCADE"), unique=True, nullable=False
    )
    notebook_id: Mapped[str] = mapped_column(String(200), nullable=False)
    account_email: Mapped[str | None] = mapped_column(String(320))
    session_ciphertext: Mapped[str | None] = mapped_column(Text)
    paper: Mapped[dict[str, object]] = mapped_column(JSON_TYPE, nullable=False)
    resolved_pdf_url: Mapped[str | None] = mapped_column(String(2048))
    source_id: Mapped[str | None] = mapped_column(String(200))

    run: Mapped[ToolRun] = relationship()
