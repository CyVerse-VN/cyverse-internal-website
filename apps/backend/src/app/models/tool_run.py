from __future__ import annotations

from datetime import datetime
from uuid import UUID, uuid4

from sqlalchemy import (
    JSON,
    Boolean,
    DateTime,
    Float,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
    UniqueConstraint,
    Uuid,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base, TimestampMixin
from app.models.user import User

JSON_TYPE = JSON().with_variant(JSONB, "postgresql")


class ToolRun(TimestampMixin, Base):
    """Durable lifecycle and queue record for an internal tool execution."""

    __tablename__ = "tool_runs"
    __table_args__ = (
        Index("ix_tool_runs_queue", "tool_name", "status", "created_at"),
        UniqueConstraint("owner_id", "idempotency_key", name="uq_tool_runs_idempotency"),
    )

    id: Mapped[UUID] = mapped_column(Uuid, primary_key=True, default=uuid4)
    owner_id: Mapped[UUID] = mapped_column(
        ForeignKey("users.id", ondelete="RESTRICT"), nullable=False, index=True
    )
    tool_name: Mapped[str] = mapped_column(String(64), nullable=False)
    status: Mapped[str] = mapped_column(String(32), default="queued", nullable=False)
    current_stage: Mapped[str] = mapped_column(String(32), default="queued", nullable=False)
    progress: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)
    idempotency_key: Mapped[str | None] = mapped_column(String(64))
    cancel_requested: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    attempt_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    worker_id: Mapped[str | None] = mapped_column(String(100))
    heartbeat_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    error_code: Mapped[str | None] = mapped_column(String(64))
    error_message: Mapped[str | None] = mapped_column(Text)
    details: Mapped[dict[str, object]] = mapped_column(JSON_TYPE, default=dict, nullable=False)

    events: Mapped[list[ToolRunEvent]] = relationship(
        back_populates="run", cascade="all, delete-orphan", order_by="ToolRunEvent.sequence"
    )
    owner: Mapped[User] = relationship()


class ToolRunEvent(Base):
    """Persisted stage transition for progress recovery after reconnects."""

    __tablename__ = "tool_run_events"
    __table_args__ = (UniqueConstraint("run_id", "sequence", name="uq_tool_run_events_seq"),)

    id: Mapped[UUID] = mapped_column(Uuid, primary_key=True, default=uuid4)
    run_id: Mapped[UUID] = mapped_column(
        ForeignKey("tool_runs.id", ondelete="CASCADE"), nullable=False, index=True
    )
    sequence: Mapped[int] = mapped_column(Integer, nullable=False)
    stage: Mapped[str] = mapped_column(String(32), nullable=False)
    status: Mapped[str] = mapped_column(String(20), nullable=False)
    message: Mapped[str] = mapped_column(String(240), nullable=False)
    progress: Mapped[float] = mapped_column(Float, nullable=False)
    metadata_json: Mapped[dict[str, object]] = mapped_column(
        "metadata", JSON_TYPE, default=dict, nullable=False
    )
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)

    run: Mapped[ToolRun] = relationship(back_populates="events")
