from typing import Annotated

from fastapi import Depends

from app.auth.dependencies import get_current_user
from app.auth.errors import PermissionDeniedError
from app.models.user import ROLE_ADMIN, User


async def require_admin(
    user: Annotated[User, Depends(get_current_user)],
) -> User:
    if user.role != ROLE_ADMIN:
        raise PermissionDeniedError
    return user
