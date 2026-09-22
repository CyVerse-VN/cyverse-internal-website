from typing import Annotated

from fastapi import Depends
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.errors import AuthenticationRequiredError
from app.auth.repository import AuthRepository
from app.auth.service import AuthService
from app.db.session import get_db_session
from app.models.user import User

bearer_scheme = HTTPBearer(auto_error=False)


def get_auth_service(
    session: Annotated[AsyncSession, Depends(get_db_session)],
) -> AuthService:
    return AuthService(AuthRepository(session))


async def get_current_user(
    credentials: Annotated[HTTPAuthorizationCredentials | None, Depends(bearer_scheme)],
    service: Annotated[AuthService, Depends(get_auth_service)],
) -> User:
    if credentials is None or credentials.scheme.lower() != "bearer":
        raise AuthenticationRequiredError
    return await service.authenticate_access_token(credentials.credentials)
