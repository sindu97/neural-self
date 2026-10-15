"""Dependencies for authenticating and authorizing API requests."""

from typing import Annotated

from fastapi import Depends
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.orm import Session

from neuralshelf.core.exceptions import AuthenticationError, PermissionDeniedError
from neuralshelf.core.security import decode_access_token
from neuralshelf.db.session import get_db
from neuralshelf.features.users.models import User
from neuralshelf.features.users.repository import UserRepository

bearer_scheme = HTTPBearer(auto_error=False)


def get_current_user(
    credentials: Annotated[
        HTTPAuthorizationCredentials | None,
        Depends(bearer_scheme),
    ],
    db: Annotated[Session, Depends(get_db)],
) -> User:
    """Return the authenticated user or reject the request with 401."""
    if credentials is None:
        raise AuthenticationError()

    try:
        user_id = decode_access_token(credentials.credentials)
    except ValueError:
        raise AuthenticationError() from None

    user = UserRepository(db).get_by_id(user_id)

    if user is None:
        raise AuthenticationError()

    return user


def require_admin(current_user: Annotated[User, Depends(get_current_user)]) -> User:
    """Allow only administrators; others get 403."""
    if not current_user.is_admin:
        raise PermissionDeniedError()
    return current_user
