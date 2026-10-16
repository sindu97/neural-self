
"""Database operations for user accounts."""

from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

from neuralshelf.features.users.models import User


class UserRepository:
    """Encapsulate database access for users."""

    def __init__(self, db: Session) -> None:
        self.db = db

    def get_by_email(self, email: str) -> User | None:
        """Find a user by email address."""
        statement = select(User).where(User.email == email)
        return self.db.scalar(statement)

    def get_by_id(self, user_id: UUID) -> User | None:
        """Find a user by ID."""
        statement = select(User).where(User.id == user_id)
        return self.db.scalar(statement)

    def create(
        self,
        *,
        name: str,
        email: str,
        password_hash: str,
    ) -> User:
        """Persist a new user."""
        user = User(
            name=name,
            email=email,
            password_hash=password_hash,
        )

        self.db.add(user)
        self.db.flush()
        self.db.refresh(user)

        return user

    def set_admin(self, user: User, *, is_admin: bool) -> None:
        """Set the administrator flag (flushed, not committed)."""
        user.is_admin = is_admin
        self.db.flush()
