from __future__ import annotations

from datetime import date
from uuid import UUID, uuid4

from sqlalchemy import (
    JSON,
    Boolean,
    Date,
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
from app.models.tool_run import ToolRun

JSON_TYPE = JSON().with_variant(JSONB, "postgresql")


class ResearchSession(TimestampMixin, Base):
    __tablename__ = "research_sessions"
    __table_args__ = (
        Index("ix_research_sessions_visibility_created", "visibility", "created_at"),
    )

    id: Mapped[UUID] = mapped_column(Uuid, primary_key=True, default=uuid4)
    run_id: Mapped[UUID] = mapped_column(
        ForeignKey("tool_runs.id", ondelete="CASCADE"), unique=True, nullable=False
    )
    query: Mapped[str] = mapped_column(Text, nullable=False)
    title: Mapped[str] = mapped_column(String(120), nullable=False)
    visibility: Mapped[str] = mapped_column(String(16), default="public", nullable=False)
    effective_settings: Mapped[dict[str, object]] = mapped_column(
        JSON_TYPE, default=dict, nullable=False
    )
    pipeline_version: Mapped[str] = mapped_column(String(20), default="3.0.0", nullable=False)
    warnings: Mapped[list[object]] = mapped_column(JSON_TYPE, default=list, nullable=False)
    result_stats: Mapped[dict[str, object]] = mapped_column(JSON_TYPE, default=dict, nullable=False)

    run: Mapped[ToolRun] = relationship()
    papers: Mapped[list[ResearchPaper]] = relationship(
        back_populates="session", cascade="all, delete-orphan", order_by="ResearchPaper.rank"
    )


class ResearchPaper(Base):
    __tablename__ = "research_papers"
    __table_args__ = (
        UniqueConstraint("session_id", "rank", name="uq_research_papers_rank"),
        UniqueConstraint("session_id", "dedup_key", name="uq_research_papers_dedup"),
    )

    id: Mapped[UUID] = mapped_column(Uuid, primary_key=True, default=uuid4)
    session_id: Mapped[UUID] = mapped_column(
        ForeignKey("research_sessions.id", ondelete="CASCADE"), nullable=False, index=True
    )
    rank: Mapped[int] = mapped_column(Integer, nullable=False)
    relevance_score: Mapped[float] = mapped_column(Float, nullable=False)
    read_priority: Mapped[str] = mapped_column(String(16), nullable=False)
    dedup_key: Mapped[str] = mapped_column(String(512), nullable=False)
    title: Mapped[str] = mapped_column(String(1000), nullable=False)
    authors: Mapped[list[object]] = mapped_column(JSON_TYPE, default=list, nullable=False)
    year: Mapped[int | None] = mapped_column(Integer)
    published_at: Mapped[date | None] = mapped_column(Date)
    venue: Mapped[str | None] = mapped_column(String(500))
    doi: Mapped[str | None] = mapped_column(String(300))
    arxiv_id: Mapped[str | None] = mapped_column(String(100))
    sources: Mapped[list[object]] = mapped_column(JSON_TYPE, default=list, nullable=False)
    paper_type: Mapped[str] = mapped_column(String(32), nullable=False)
    fields: Mapped[list[object]] = mapped_column(JSON_TYPE, default=list, nullable=False)
    citation_count: Mapped[int | None] = mapped_column(Integer)
    is_open_access: Mapped[bool | None] = mapped_column(Boolean)
    pdf_url: Mapped[str | None] = mapped_column(String(2048))
    landing_url: Mapped[str | None] = mapped_column(String(2048))
    summary_vi: Mapped[str] = mapped_column(Text, nullable=False)
    why_read_vi: Mapped[list[object]] = mapped_column(JSON_TYPE, nullable=False)

    session: Mapped[ResearchSession] = relationship(back_populates="papers")
