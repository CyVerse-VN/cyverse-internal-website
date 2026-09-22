from uuid import UUID

from sqlalchemy import func, or_, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.user import ROLE_ADMIN, User


class AuthRepository:
    """Persistence boundary for internal users."""

    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def get_user_by_username(self, username: str) -> User | None:
        return await self.session.scalar(
            select(User).where(User.username == username, User.deleted_at.is_(None))
        )

    async def get_user_by_id(self, user_id: UUID) -> User | None:
        return await self.session.scalar(
            select(User).where(User.id == user_id, User.deleted_at.is_(None))
        )

    async def list_users(
        self, *, query: str | None, offset: int, limit: int
    ) -> tuple[list[User], int]:
        filters = []
        if query:
            search = f"%{query.lower()}%"
            filters.append(
                or_(
                    func.lower(User.username).like(search),
                    func.lower(User.display_name).like(search),
                    func.lower(func.coalesce(User.team, "")).like(search),
                )
            )

        statement = (
            select(User)
            .where(User.deleted_at.is_(None))
            .order_by(User.created_at.desc())
            .offset(offset)
            .limit(limit)
        )
        count_statement = select(func.count()).select_from(User).where(User.deleted_at.is_(None))
        if filters:
            statement = statement.where(*filters)
            count_statement = count_statement.where(*filters)

        users = list((await self.session.scalars(statement)).all())
        total = int((await self.session.scalar(count_statement)) or 0)
        return users, total

    async def count_active_admins(self) -> int:
        statement = (
            select(func.count())
            .select_from(User)
            .where(User.role == ROLE_ADMIN, User.is_active.is_(True), User.deleted_at.is_(None))
        )
        return int((await self.session.scalar(statement)) or 0)

    def add_user(self, user: User) -> None:
        self.session.add(user)

    async def flush(self) -> None:
        await self.session.flush()

    async def commit(self) -> None:
        await self.session.commit()

    async def rollback(self) -> None:
        await self.session.rollback()


__all__ = ["AuthRepository", "IntegrityError"]
