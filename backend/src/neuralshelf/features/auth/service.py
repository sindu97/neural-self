
"""Business logic for user authentication."""

from datetime import UTC, datetime

from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from neuralshelf.core.exceptions import ApplicationError
from neuralshelf.core.messages import Message, MessageCode
from neuralshelf.core.security import (
    create_access_token,
    create_refresh_token,
    hash_password,
    hash_refresh_token,
    verify_password,
)
from neuralshelf.features.auth.models import RefreshToken
from neuralshelf.features.auth.repository import RefreshTokenRepository
from neuralshelf.features.users.models import User
from neuralshelf.features.users.repository import UserRepository
from neuralshelf.features.users.schemas import UserResponse


class EmailAlreadyRegisteredError(ApplicationError):
    """Raised when an email address is already registered."""

    def __init__(self, message: str = Message.EMAIL_ALREADY_REGISTERED) -> None:
        super().__init__(
            message=message,
            code=MessageCode.EMAIL_ALREADY_REGISTERED,
            status_code=409,
        )


class InvalidCredentialsError(ApplicationError):
    """Raised when login credentials are invalid."""

    def __init__(self) -> None:
        super().__init__(
            message=Message.INVALID_CREDENTIALS,
            code=MessageCode.INVALID_CREDENTIALS,
            status_code=401,
        )


class InvalidRefreshTokenError(ApplicationError):
    """Raised when a refresh token is unknown, expired, or revoked."""

    def __init__(self) -> None:
        super().__init__(
            message=Message.INVALID_REFRESH_TOKEN,
            code=MessageCode.INVALID_REFRESH_TOKEN,
            status_code=401,
        )


class AuthService:
    """Handle authentication-related business operations."""

    def __init__(self, db: Session) -> None:
        self.db = db
        self.user_repository = UserRepository(db)
        self.refresh_token_repository = RefreshTokenRepository(db)

    def signup(
        self,
        *,
        name: str,
        email: str,
        password: str,
    ) -> User:
        """Register a user with a securely hashed password."""
        existing_user = self.user_repository.get_by_email(email)

        if existing_user is not None:
            raise EmailAlreadyRegisteredError(
                "An account with this email already exists."
            )

        password_hash = hash_password(password)

        try:
            user = self.user_repository.create(
                name=name,
                email=email,
                password_hash=password_hash,
            )
            self.db.commit()
            self.db.refresh(user)
            return user

        except IntegrityError as exc:
            self.db.rollback()

            # Handles concurrent signup requests that bypass the
            # initial duplicate-email check.
            raise EmailAlreadyRegisteredError(
                "An account with this email already exists."
            ) from exc

    def login(self, *, email: str, password: str) -> dict:
        """Check credentials and issue tokens.

        Raises:
            InvalidCredentialsError: Unknown email or wrong password. Both give the
                same error, so the response never reveals which accounts exist.
        """
        user = self.user_repository.get_by_email(email)

        if user is None or not verify_password(password, user.password_hash):
            raise InvalidCredentialsError()

        tokens, _ = self._issue_tokens(user)
        self.db.commit()

        return {
            **tokens,
            "user": UserResponse.model_validate(user).model_dump(mode="json"),
        }

    def refresh(self, *, refresh_token: str) -> dict:
        """Exchange a valid refresh token for a new access/refresh token pair.

        The presented refresh token is rotated: it is revoked and replaced.
        Reusing an already-revoked token is treated as theft, so every
        session belonging to that user is revoked.
        """
        stored_token = self.refresh_token_repository.get_by_hash(
            hash_refresh_token(refresh_token)
        )

        if stored_token is None:
            raise InvalidRefreshTokenError()

        if stored_token.revoked_at is not None:
            self.refresh_token_repository.revoke_all_for_user(stored_token.user_id)
            self.db.commit()
            raise InvalidRefreshTokenError()

        if stored_token.expires_at <= datetime.now(UTC):
            raise InvalidRefreshTokenError()

        user = self.user_repository.get_by_id(stored_token.user_id)

        if user is None:
            raise InvalidRefreshTokenError()

        self.refresh_token_repository.revoke(stored_token)
        tokens, new_token = self._issue_tokens(user)
        stored_token.replaced_by_token_id = new_token.id
        self.db.commit()

        # Web clients keep the access token only in memory, so after a page
        # reload this is how they find out who is logged in.
        return {**tokens, "user": UserResponse.model_validate(user).model_dump(mode="json")}

    def revoke(self, *, refresh_token: str) -> None:
        """Revoke a refresh token (logout).

        Unknown or already-revoked tokens are ignored so the endpoint does
        not reveal whether a token exists (RFC 7009).
        """
        stored_token = self.refresh_token_repository.get_by_hash(
            hash_refresh_token(refresh_token)
        )

        if stored_token is None:
            return

        self.refresh_token_repository.revoke(stored_token)
        self.db.commit()

    def _issue_tokens(self, user: User) -> tuple[dict, RefreshToken]:
        """Create an access token and a persisted refresh token for a user."""
        access_token, expires_in = create_access_token(user.id)
        refresh_token, refresh_expires_at = create_refresh_token()

        refresh_token_record = self.refresh_token_repository.create(
            user_id=user.id,
            token_hash=hash_refresh_token(refresh_token),
            expires_at=refresh_expires_at,
        )

        return {
            "access_token": access_token,
            "refresh_token": refresh_token,
            "token_type": "bearer",
            "expires_in": expires_in,
            "refresh_expires_at": refresh_expires_at.isoformat(),
        }, refresh_token_record
