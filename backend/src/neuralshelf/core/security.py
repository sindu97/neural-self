"""Security utilities for password hashing and JWT authentication."""

import hashlib
import secrets
from datetime import UTC, datetime, timedelta
from typing import Any
from uuid import UUID

import jwt
from pwdlib import PasswordHash

from neuralshelf.core.config import get_settings

_password_hash = PasswordHash.recommended()

ACCESS_TOKEN_TYPE = "access"
REFRESH_TOKEN_BYTES = 48


def hash_password(password: str) -> str:
    return _password_hash.hash(password)


def verify_password(password: str, password_hash: str) -> bool:
    return _password_hash.verify(password, password_hash)


def create_access_token(user_id: UUID) -> tuple[str, int]:
    settings = get_settings()
    expires_in = settings.access_token_expire_minutes * 60
    issued_at = datetime.now(UTC)
    expires_at = issued_at + timedelta(seconds=expires_in)

    payload: dict[str, Any] = {
        "sub": str(user_id),
        "type": ACCESS_TOKEN_TYPE,
        "iat": issued_at,
        "exp": expires_at,
    }

    token = jwt.encode(
        payload,
        settings.jwt_secret_key.get_secret_value(),
        algorithm=settings.jwt_algorithm,
    )
    return token, expires_in


def create_refresh_token() -> tuple[str, datetime]:
    """Return a new opaque refresh token and its expiry time."""
    settings = get_settings()
    token = secrets.token_urlsafe(REFRESH_TOKEN_BYTES)
    expires_at = datetime.now(UTC) + timedelta(
        days=settings.refresh_token_expire_days
    )
    return token, expires_at


def hash_refresh_token(token: str) -> str:
    """Hash a refresh token for storage; only the hash is persisted."""
    return hashlib.sha256(token.encode("utf-8")).hexdigest()


def decode_access_token(token: str) -> UUID:
    """Validate an access JWT and return its user ID."""
    settings = get_settings()

    try:
        payload = jwt.decode(
            token,
            settings.jwt_secret_key.get_secret_value(),
            algorithms=[settings.jwt_algorithm],
            options={"require": ["sub", "exp", "iat", "type"]},
        )

        if payload.get("type") != ACCESS_TOKEN_TYPE:
            raise ValueError("Invalid access token type.")

        return UUID(payload["sub"])

    except (jwt.InvalidTokenError, TypeError, KeyError, ValueError) as exc:
        raise ValueError("Invalid or expired access token.") from exc