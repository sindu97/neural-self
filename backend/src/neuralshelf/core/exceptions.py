"""Application-level exceptions."""

from neuralshelf.core.messages import Message, MessageCode


class ApplicationError(Exception):
    """Base exception for expected application errors."""

    def __init__(
        self,
        message: str,
        code: str,
        status_code: int = 400,
        headers: dict[str, str] | None = None,
    ) -> None:
        super().__init__(message)
        self.message = message
        self.code = code
        self.status_code = status_code
        self.headers = headers


class AuthenticationError(ApplicationError):
    """Missing, invalid or expired access token."""

    def __init__(self) -> None:
        super().__init__(
            message=Message.AUTHENTICATION_REQUIRED,
            code=MessageCode.UNAUTHORIZED,
            status_code=401,
            headers={"WWW-Authenticate": "Bearer"},
        )


class PermissionDeniedError(ApplicationError):
    """Authenticated, but not allowed to perform this action."""

    def __init__(self) -> None:
        super().__init__(
            message=Message.PERMISSION_DENIED,
            code=MessageCode.FORBIDDEN,
            status_code=403,
        )


class RateLimitExceededError(ApplicationError):
    """Too many requests for one rate-limit key (HTTP 429, with Retry-After)."""

    def __init__(self, retry_after_seconds: int) -> None:
        super().__init__(
            message=Message.RATE_LIMITED,
            code=MessageCode.RATE_LIMITED,
            status_code=429,
            headers={"Retry-After": str(retry_after_seconds)},
        )


class EmbeddingServiceError(ApplicationError):
    """Raised when the embedding provider cannot produce embeddings."""

    def __init__(self) -> None:
        super().__init__(
            message=Message.EMBEDDING_SERVICE_UNAVAILABLE,
            code=MessageCode.EMBEDDING_SERVICE_UNAVAILABLE,
            status_code=503,
        )


class LLMServiceError(ApplicationError):
    """Raised when the language model provider cannot generate an answer."""

    def __init__(self) -> None:
        super().__init__(
            message=Message.LLM_SERVICE_UNAVAILABLE,
            code=MessageCode.LLM_SERVICE_UNAVAILABLE,
            status_code=503,
        )
