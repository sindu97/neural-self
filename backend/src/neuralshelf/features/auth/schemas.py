"""Request and response schemas for authentication."""

from pydantic import BaseModel, EmailStr, Field, field_validator


class SignupRequest(BaseModel):
    """Validate incoming signup data."""

    name: str = Field(min_length=2, max_length=100)
    email: EmailStr
    password: str = Field(min_length=8, max_length=128)

    @field_validator("name")
    @classmethod
    def normalize_name(cls, value: str) -> str:
        """Collapse runs of whitespace; at least 2 characters must remain."""
        value = " ".join(value.split())

        if len(value) < 2:
            raise ValueError("Name must contain at least 2 characters")

        return value

    @field_validator("email")
    @classmethod
    def normalize_email(cls, value: EmailStr) -> EmailStr:
        """Trim and lowercase, so emails are unique regardless of case."""
        return str(value).strip().lower()


class LoginRequest(BaseModel):
    """Credentials for ``POST /auth/login``."""

    email: EmailStr
    password: str = Field(min_length=1, max_length=128)

    @field_validator("email")
    @classmethod
    def normalize_email(cls, value: EmailStr) -> EmailStr:
        """Trim and lowercase, matching how emails are stored."""
        return str(value).strip().lower()


class RefreshTokenRequest(BaseModel):
    """Body form of the refresh token, for native clients.

    Web clients send no body: the token comes from the httpOnly cookie.
    """

    refresh_token: str | None = Field(default=None, min_length=1, max_length=512)


class RevokeTokenRequest(RefreshTokenRequest):
    """Refresh token to revoke; from the body (native) or the cookie (web)."""

