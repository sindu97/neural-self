"""Operational actions on the ingestion job queue."""

import logging
from collections.abc import Sequence
from typing import Any
from uuid import UUID

from sqlalchemy import Row
from sqlalchemy.orm import Session

from neuralshelf.core.exceptions import ApplicationError
from neuralshelf.core.messages import Message, MessageCode
from neuralshelf.features.documents.exceptions import DocumentBusyError
from neuralshelf.features.documents.job_repository import JobRepository
from neuralshelf.features.documents.models import Document, IngestionJob, JobStatus
from neuralshelf.features.documents.service import requeue_document

logger = logging.getLogger(__name__)


class JobNotFoundError(ApplicationError):
    def __init__(self) -> None:
        super().__init__(
            message=Message.JOB_NOT_FOUND, code=MessageCode.JOB_NOT_FOUND, status_code=404
        )


class JobNotFailedError(ApplicationError):
    def __init__(self) -> None:
        super().__init__(
            message=Message.JOB_NOT_FAILED, code=MessageCode.JOB_NOT_FAILED, status_code=409
        )


class AdminJobService:
    def __init__(self, db: Session) -> None:
        self.db = db
        self.jobs = JobRepository(db)

    def list_jobs(
        self, *, status: JobStatus | None, limit: int, offset: int
    ) -> tuple[Sequence[Row], int]:
        return self.jobs.list_with_documents(status=status, limit=limit, offset=offset)

    def stats(self) -> dict[str, Any]:
        return self.jobs.stats()

    def retry_job(self, job_id: UUID) -> IngestionJob:
        """Queue a new attempt for the document of a failed job; returns the new job."""
        job = self.jobs.get(job_id)
        if job is None:
            raise JobNotFoundError()
        if job.status != JobStatus.FAILED:
            raise JobNotFailedError()

        document = self.db.get(Document, job.document_id)
        if document is None:
            raise JobNotFoundError()
        requeue_document(self.db, document)
        logger.info("Admin requeued document %s (failed job %s).", document.id, job_id)

        new_job = self.jobs.get_active_for_document(document.id)
        if new_job is None:  # a worker can't have finished it yet, but don't assume
            raise JobNotFoundError()
        return new_job

    def retry_all_failed(self, *, limit: int) -> list[UUID]:
        """Requeue up to ``limit`` failed documents, e.g. after an outage is fixed."""
        requeued: list[UUID] = []
        for document_id in self.jobs.failed_document_ids_without_active_job(limit=limit):
            document = self.db.get(Document, document_id)
            if document is None:
                continue
            try:
                requeue_document(self.db, document)
            except DocumentBusyError:
                continue  # someone requeued it concurrently
            requeued.append(document_id)

        logger.info("Admin bulk-requeued %d failed document(s).", len(requeued))
        return requeued
