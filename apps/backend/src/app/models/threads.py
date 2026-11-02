from __future__ import annotations

from datetime import datetime
from uuid import UUID, uuid4

from sqlalchemy import Boolean, DateTime, ForeignKey, Index, Integer, String, UniqueConstraint, Uuid
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base
from app.models.tool_run import JSON_TYPE


class ThreadsResultRecord(Base):
    """Session metadata and incremental snapshots, owned through a tool run."""

    __tablename__ = "threads_results"
    __table_args__ = (
        Index("ix_threads_results_storage", "deletion_requested", "next_storage_attempt_at"),
    )

    run_id: Mapped[UUID] = mapped_column(
        ForeignKey("tool_runs.id", ondelete="CASCADE"), primary_key=True
    )
    summary: Mapped[dict[str, object]] = mapped_column(JSON_TYPE, nullable=False)
    visibility: Mapped[str] = mapped_column(String(16), default="public", nullable=False)
    snapshot_ready: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    post_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    comment_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    archive_status: Mapped[str] = mapped_column(String(16), default="pending", nullable=False)
    archive_public_id: Mapped[str | None] = mapped_column(String(200))
    legacy_archive_public_id: Mapped[str | None] = mapped_column(String(200))
    archive_uploaded_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    storage_error: Mapped[str | None] = mapped_column(String(64))
    next_storage_attempt_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    storage_attempt_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    deletion_requested: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    posts: Mapped[list[ThreadsPostRecord]] = relationship(
        cascade="all, delete-orphan", order_by="ThreadsPostRecord.position", lazy="raise"
    )


class ThreadsPostRecord(Base):
    __tablename__ = "threads_posts"
    __table_args__ = (
        UniqueConstraint("run_id", "post_id", name="uq_threads_posts_source"),
        UniqueConstraint("run_id", "position", name="uq_threads_posts_position"),
    )

    id: Mapped[UUID] = mapped_column(Uuid, primary_key=True, default=uuid4)
    run_id: Mapped[UUID] = mapped_column(
        ForeignKey("threads_results.run_id", ondelete="CASCADE"), nullable=False, index=True
    )
    post_id: Mapped[str] = mapped_column(String(128), nullable=False)
    position: Mapped[int] = mapped_column(Integer, nullable=False)
    data: Mapped[dict[str, object]] = mapped_column(JSON_TYPE, nullable=False)
    comments: Mapped[list[ThreadsCommentRecord]] = relationship(
        cascade="all, delete-orphan", order_by="ThreadsCommentRecord.position", lazy="raise"
    )


class ThreadsCommentRecord(Base):
    __tablename__ = "threads_comments"
    __table_args__ = (
        UniqueConstraint("post_record_id", "comment_id", name="uq_threads_comments_source"),
        UniqueConstraint("post_record_id", "position", name="uq_threads_comments_position"),
    )

    id: Mapped[UUID] = mapped_column(Uuid, primary_key=True, default=uuid4)
    post_record_id: Mapped[UUID] = mapped_column(
        ForeignKey("threads_posts.id", ondelete="CASCADE"), nullable=False, index=True
    )
    comment_id: Mapped[str] = mapped_column(String(128), nullable=False)
    parent_comment_id: Mapped[str | None] = mapped_column(String(128))
    position: Mapped[int] = mapped_column(Integer, nullable=False)
    data: Mapped[dict[str, object]] = mapped_column(JSON_TYPE, nullable=False)
