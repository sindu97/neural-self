"""Schemas for administrator endpoints."""

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel

from neuralshelf.features.documents.models import JobStatus


class IngestionJobResponse(BaseModel):
    """A job as seen by administrators, including the internal error detail."""

    id: UUID
    document_id: UUID
    user_id: UUID
    filename: str
    status: JobStatus
    attempts: int
    max_attempts: int
    last_error: str | None
    locked_by: str | None
    available_at: datetime
    created_at: datetime
    updated_at: datetime | None


class JobStatsResponse(BaseModel):
    """Ingestion queue health for administrators."""

    counts: dict[str, int]
    oldest_due_job_age_seconds: float
    running_with_expired_lease: int


class BulkRetryResponse(BaseModel):
    """Result of requeueing failed documents."""

    requeued: int
    document_ids: list[UUID]
