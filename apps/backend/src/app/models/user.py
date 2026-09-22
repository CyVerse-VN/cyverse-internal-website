from __future__ import annotations

from datetime import datetime
from uuid import UUID, uuid4

from sqlalchemy import Boolean, DateTime, Index, Integer, String, Uuid
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base, TimestampMixin

ROLE_ADMIN = "admin"
ROLE_MEMBER = "member"
VALID_USER_ROLES = frozenset({ROLE_ADMIN, ROLE_MEMBER})


class User(TimestampMixin, Base):
    """Internal account managed by CyVerse administrators."""

    __tablename__ = "users"
    __table_args__ = (Index("ix_users_username", "username", unique=True),)

    id: Mapped[UUID] = mapped_column(Uuid, primary_key=True, default=uuid4)
    username: Mapped[str] = mapped_column(String(64), nullable=False)
    password_hash: Mapped[str] = mapped_column(String(512), nullable=False)
    display_name: Mapped[str] = mapped_column(String(100), nullable=False)
    team: Mapped[str | None] = mapped_column(String(100))
    role: Mapped[str] = mapped_column(String(16), default=ROLE_MEMBER, nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    last_login_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    token_version: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
