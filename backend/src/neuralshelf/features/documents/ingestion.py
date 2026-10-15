"""Ingestion job execution: parse PDF -> chunk -> embed -> store chunks.

Runs in the worker process (see ``neuralshelf.workers.ingestion_worker``).
Processing is idempotent: chunks are replaced in a single transaction, so a
job interrupted at any point can safely run again from the start.
"""

import logging
import random
from dataclasses import dataclass

from sqlalchemy.exc import OperationalError
from sqlalchemy.orm import Session, sessionmaker

from neuralshelf.core.config import get_settings
from neuralshelf.core.exceptions import ApplicationError, EmbeddingServiceError
from neuralshelf.core.messages import Message
from neuralshelf.features.documents.chunking import chunk_pages
from neuralshelf.features.documents.exceptions import IngestionError
from neuralshelf.features.documents.job_repository import JobRepository
from neuralshelf.features.documents.models import DocumentStatus, IngestionJob
from neuralshelf.features.documents.repository import DocumentRepository
from neuralshelf.features.documents.storage import LocalFileStorage
from neuralshelf.integrations.embeddings.ollama import EmbeddingClient
from neuralshelf.integrations.parsers.pdf import extract_pdf_pages

logger = logging.getLogger(__name__)

# Failures worth retrying: the provider or database may recover.
TRANSIENT_ERRORS: tuple[type[Exception], ...] = (EmbeddingServiceError, OperationalError)


class LeaseLostError(Exception):
    """This worker no longer owns the job; another worker has taken it over."""


@dataclass(frozen=True)
class JobContext:
    session_factory: sessionmaker[Session]
    storage: LocalFileStorage
    embedder: EmbeddingClient
    worker_id: str


def retry_delay_seconds(attempt: int) -> float:
    """Exponential backoff with jitter: ~base, 2x base, 4x base ... capped.

    Jitter spreads out retries so many failed jobs don't hit a recovering
    service at the same instant.
    """
    settings = get_settings()
    delay = min(
        settings.job_retry_max_seconds,
        settings.job_retry_base_seconds * 2 ** (attempt - 1),
    )
    return delay * random.uniform(0.5, 1.0)


def run_ingestion_job(job: IngestionJob, context: JobContext) -> None:
    """Execute one claimed job and record its outcome; never raises."""
    if job.attempts > job.max_attempts:
        # Reclaimed after its worker died on the final attempt (e.g. a document
        # that crashes the process every time). Stop retrying it.
        _finish_failed(job, context, Message.INGESTION_FAILED, "max attempts exceeded")
        return

    try:
        _process(job, context)
        logger.info("Job %s succeeded (attempt %d).", job.id, job.attempts)
    except LeaseLostError:
        logger.warning("Job %s lease lost; leaving it to its new owner.", job.id)
    except Exception as exc:
        _handle_failure(job, context, exc)


def _process(job: IngestionJob, context: JobContext) -> None:
    settings = get_settings()

    with context.session_factory() as db:
        document = DocumentRepository(db).get(job.document_id)
        if document is None or document.storage_key is None:
            raise IngestionError(Message.DOCUMENT_NOT_FOUND)
        document.status = DocumentStatus.PROCESSING
        document.error_message = None
        db.commit()
        storage_key = document.storage_key

    path = context.storage.path_for(storage_key)
    if not path.exists():
        raise IngestionError(Message.FILE_UNREADABLE)
    try:
        pages = extract_pdf_pages(path)
    except Exception as exc:
        raise IngestionError(Message.FILE_UNREADABLE) from exc

    chunks = chunk_pages(
        pages,
        chunk_size=settings.chunk_size_chars,
        overlap=settings.chunk_overlap_chars,
    )
    if not chunks:
        raise IngestionError(Message.INGESTION_NO_TEXT)

    embeddings = context.embedder.embed_documents([chunk.content for chunk in chunks])

    # Commit point: lease check, chunk replacement and status changes all
    # happen in one transaction, so the outcome is all-or-nothing.
    with context.session_factory() as db:
        if not JobRepository(db).mark_succeeded(job_id=job.id, worker_id=context.worker_id):
            raise LeaseLostError()
        repository = DocumentRepository(db)
        repository.replace_chunks(job.document_id, chunks, embeddings)
        document = repository.get(job.document_id)
        if document is not None:
            document.status = DocumentStatus.COMPLETED
            document.error_message = None
        db.commit()


def _handle_failure(job: IngestionJob, context: JobContext, exc: Exception) -> None:
    if isinstance(exc, IngestionError):
        # Permanent: the input itself is the problem; retrying won't help.
        logger.info("Job %s failed permanently: %s", job.id, exc)
        _finish_failed(job, context, str(exc), str(exc))
        return

    public_message = exc.message if isinstance(exc, ApplicationError) else Message.INGESTION_FAILED
    internal_error = f"{type(exc).__name__}: {exc}"
    is_transient = isinstance(exc, TRANSIENT_ERRORS)

    if job.attempts >= job.max_attempts:
        logger.error("Job %s failed after %d attempts: %s", job.id, job.attempts, internal_error)
        _finish_failed(job, context, public_message, internal_error)
        return

    if is_transient:
        logger.warning("Job %s attempt %d failed transiently: %s", job.id, job.attempts, exc)
    else:
        # Unknown errors are retried too (bounded by max_attempts), with a full traceback.
        logger.exception("Job %s attempt %d failed unexpectedly.", job.id, job.attempts)

    delay = retry_delay_seconds(job.attempts)
    try:
        with context.session_factory() as db:
            if JobRepository(db).schedule_retry(
                job_id=job.id,
                worker_id=context.worker_id,
                error=internal_error,
                delay_seconds=delay,
            ):
                db.commit()
                logger.info("Job %s will retry in %.0fs.", job.id, delay)
    except Exception:
        # If even this fails the lease simply expires and the job is reclaimed.
        logger.exception("Could not schedule retry for job %s.", job.id)


def _finish_failed(
    job: IngestionJob, context: JobContext, public_message: str, internal_error: str
) -> None:
    try:
        with context.session_factory() as db:
            if not JobRepository(db).mark_failed(
                job_id=job.id, worker_id=context.worker_id, error=internal_error
            ):
                return
            document = DocumentRepository(db).get(job.document_id)
            if document is not None:
                document.status = DocumentStatus.FAILED
                document.error_message = public_message
            db.commit()
    except Exception:
        logger.exception("Could not record failure for job %s.", job.id)
