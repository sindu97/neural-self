
"""Database operations for refresh tokens."""

from datetime import UTC, datetime
from uuid import UUID

from sqlalchemy import select, update
from sqlalchemy.orm import Session

from neuralshelf.features.auth.models import RefreshToken


class RefreshTokenRepository:
    """Encapsulate database access for refresh tokens."""

    def __init__(self, db: Session) -> None:
        self.db = db

    def get_by_hash(self, token_hash: str) -> RefreshToken | None:
        """Find a refresh token by its hash."""
        statement = select(RefreshToken).where(RefreshToken.token_hash == token_hash)
        return self.db.scalar(statement)

    def create(
        self,
        *,
        user_id: UUID,
        token_hash: str,
        expires_at: datetime,
    ) -> RefreshToken:
        """Persist a new refresh token."""
        refresh_token = RefreshToken(
            user_id=user_id,
            token_hash=token_hash,
            expires_at=expires_at,
        )

        self.db.add(refresh_token)
        self.db.flush()

        return refresh_token

    def revoke(self, refresh_token: RefreshToken) -> None:
        """Mark a single refresh token as revoked."""
        if refresh_token.revoked_at is None:
            refresh_token.revoked_at = datetime.now(UTC)
            self.db.flush()

    def revoke_all_for_user(self, user_id: UUID) -> None:
        """Revoke every active refresh token belonging to a user."""
        statement = (
            update(RefreshToken)
            .where(
                RefreshToken.user_id == user_id,
                RefreshToken.revoked_at.is_(None),
            )
            .values(revoked_at=datetime.now(UTC))
        )
        self.db.execute(statement)
