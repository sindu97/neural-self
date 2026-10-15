
from datetime import UTC, datetime

from neuralshelf.core.security import (
    create_refresh_token,
    hash_password,
    hash_refresh_token,
    verify_password,
)


def test_hash_password_does_not_return_plaintext() -> None:
    password = "TestPassword!123"

    password_hash = hash_password(password)

    assert password_hash != password


def test_verify_password_accepts_correct_password() -> None:
    password = "TestPassword!123"
    password_hash = hash_password(password)

    assert verify_password(password, password_hash) is True


def test_verify_password_rejects_wrong_password() -> None:
    password_hash = hash_password("TestPassword!123")

    assert verify_password("WrongPassword!123", password_hash) is False


def test_create_refresh_token_returns_unique_future_tokens() -> None:
    first_token, expires_at = create_refresh_token()
    second_token, _ = create_refresh_token()

    assert first_token != second_token
    assert expires_at > datetime.now(UTC)


def test_hash_refresh_token_is_deterministic_and_not_plaintext() -> None:
    token, _ = create_refresh_token()

    assert hash_refresh_token(token) == hash_refresh_token(token)
    assert hash_refresh_token(token) != token
