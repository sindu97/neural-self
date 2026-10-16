"""Errors raised by the documents feature."""

from neuralshelf.core.exceptions import ApplicationError
from neuralshelf.core.messages import Message, MessageCode


class DocumentNotFoundError(ApplicationError):
    """Raised for missing documents and documents owned by another user alike."""

    def __init__(self) -> None:
        super().__init__(
            message=Message.DOCUMENT_NOT_FOUND,
            code=MessageCode.DOCUMENT_NOT_FOUND,
            status_code=404,
        )


class DocumentBusyError(ApplicationError):
    """Raised when an action conflicts with ingestion already in progress."""

    def __init__(self) -> None:
        super().__init__(
            message=Message.DOCUMENT_BUSY,
            code=MessageCode.DOCUMENT_BUSY,
            status_code=409,
        )


class InvalidFileError(ApplicationError):
    """Raised when an upload is not an acceptable PDF."""

    def __init__(self, message: str) -> None:
        super().__init__(message=message, code=MessageCode.INVALID_FILE, status_code=422)


class FileTooLargeError(ApplicationError):
    """The upload exceeds MAX_UPLOAD_SIZE_MB (HTTP 413)."""

    def __init__(self, max_mb: int) -> None:
        super().__init__(
            message=Message.FILE_TOO_LARGE.format(max_mb=max_mb),
            code=MessageCode.FILE_TOO_LARGE,
            status_code=413,
        )


class IngestionError(Exception):
    """Expected ingestion failure whose message is safe to show the user."""
