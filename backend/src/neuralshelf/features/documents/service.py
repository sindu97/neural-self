"""Business logic for uploading and managing documents."""

import logging
import unicodedata
import uuid
from collections.abc import Sequence
from pathlib import PurePosixPath, PureWindowsPath
from uuid import UUID

from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from neuralshelf.core.config import get_settings
from neuralshelf.core.messages import Message
from neuralshelf.features.documents.exceptions import (
    DocumentBusyError,
    DocumentNotFoundError,
    FileTooLargeError,
    InvalidFileError,
)
from neuralshelf.features.documents.job_repository import JobRepository
from neuralshelf.features.documents.models import Document, DocumentStatus
from neuralshelf.features.documents.repository import DocumentRepository
from neuralshelf.features.documents.storage import LocalFileStorage
from neuralshelf.integrations.parsers.pdf import PdfValidationError, validate_pdf_bytes

logger = logging.getLogger(__name__)

ALLOWED_CONTENT_TYPES = {"application/pdf", "application/x-pdf", "application/octet-stream"}
MAX_FILENAME_LENGTH = 255

_PDF_ERROR_MESSAGES = {
    "not_pdf": Message.FILE_NOT_PDF,
    "unreadable": Message.FILE_UNREADABLE,
    "encrypted": Message.FILE_ENCRYPTED,
    "no_pages": Message.FILE_NO_PAGES,
}


def sanitize_filename(raw: str | None) -> str:
    """Return a display-safe base filename without any client-supplied path."""
    name = PureWindowsPath(PurePosixPath(raw or "").name).name
    name = "".join(ch for ch in name if unicodedata.category(ch)[0] != "C").strip()
    if len(name) > MAX_FILENAME_LENGTH:
        stem, dot, suffix = name.rpartition(".")
        name = f"{stem[: MAX_FILENAME_LENGTH - len(suffix) - 1]}{dot}{suffix}"
    return name or "document.pdf"


def validate_upload(*, filename: str, content_type: str | None, data: bytes) -> None:
    """Reject anything that is not a non-empty, readable PDF within size limits."""
    settings = get_settings()

    if len(data) > settings.max_upload_size_bytes:
        raise FileTooLargeError(settings.max_upload_size_mb)
    if not data:
        raise InvalidFileError(Message.FILE_EMPTY)
    if not filename.lower().endswith(".pdf"):
        raise InvalidFileError(Message.FILE_NOT_PDF)
    if content_type and content_type.split(";")[0].strip().lower() not in ALLOWED_CONTENT_TYPES:
        raise InvalidFileError(Message.FILE_NOT_PDF)

    try:
        validate_pdf_bytes(data)
    except PdfValidationError as exc:
        raise InvalidFileError(_PDF_ERROR_MESSAGES[exc.reason]) from exc


class DocumentService:
    """Handle document lifecycle operations for the authenticated user."""

    def __init__(self, db: Session, storage: LocalFileStorage) -> None:
        self.db = db
        self.storage = storage
        self.repository = DocumentRepository(db)
        self.jobs = JobRepository(db)

    def upload(
        self,
        *,
        user_id: UUID,
        filename: str | None,
        content_type: str | None,
        data: bytes,
    ) -> Document:
        """Validate and store a PDF, then create its record and ingestion job.

        The document and its job are committed together, so every stored
        document is guaranteed to be picked up by a worker.
        """
        safe_filename = sanitize_filename(filename)
        validate_upload(filename=safe_filename, content_type=content_type, data=data)

        document_id = uuid.uuid4()
        storage_key = f"{user_id}/{document_id}.pdf"
        self.storage.save(storage_key, data)

        document = Document(
            id=document_id,
            user_id=user_id,
            filename=safe_filename,
            storage_key=storage_key,
            content_type="application/pdf",
            file_size_bytes=len(data),
            status=DocumentStatus.UPLOADED,
        )
        try:
            self.repository.create(document)
            self.jobs.enqueue(document_id=document_id, max_attempts=get_settings().job_max_attempts)
            self.db.commit()
        except Exception:
            self.db.rollback()
            self.storage.delete(storage_key)
            raise

        return document

    def list(self, *, user_id: UUID, limit: int, offset: int) -> tuple[Sequence[Document], int]:
        """The user's documents, newest first, and their total count."""
        return self.repository.list_owned(user_id=user_id, limit=limit, offset=offset)

    def get(self, *, user_id: UUID, document_id: UUID) -> Document:
        """The user's document.

        Raises:
            DocumentNotFoundError: Missing, or owned by another user.
        """
        document = self.repository.get_owned(user_id=user_id, document_id=document_id)
        if document is None:
            raise DocumentNotFoundError()
        return document

    def delete(self, *, user_id: UUID, document_id: UUID) -> None:
        """Delete the user's document, its chunks and its stored file."""
        document = self.get(user_id=user_id, document_id=document_id)
        storage_key = document.storage_key

        self.repository.delete(document)
        self.db.commit()

        if storage_key:
            try:
                self.storage.delete(storage_key)
            except OSError:
                logger.exception("Failed to delete stored file for document %s.", document_id)

    def reprocess(self, *, user_id: UUID, document_id: UUID) -> Document:
        """Queue a fresh ingestion job for a finished or failed document."""
        document = self.get(user_id=user_id, document_id=document_id)
        requeue_document(self.db, document)
        self.db.refresh(document)
        return document


def requeue_document(db: Session, document: Document) -> None:
    """Reset a document and queue a new ingestion job for it, then commit.

    Previous jobs are kept as history. Raises DocumentBusyError if a job is
    already queued or running.
    """
    jobs = JobRepository(db)
    if jobs.has_active_job(document.id):
        raise DocumentBusyError()

    document.status = DocumentStatus.UPLOADED
    document.error_message = None
    try:
        jobs.enqueue(document_id=document.id, max_attempts=get_settings().job_max_attempts)
        db.commit()
    except IntegrityError as exc:
        # A concurrent request queued a job first (unique active-job index).
        db.rollback()
        raise DocumentBusyError() from exc
