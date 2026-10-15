"""PostgreSQL-backed job queue for document ingestion.

Concurrency model:
- ``claim`` uses ``FOR UPDATE SKIP LOCKED``: concurrent workers never block
  on, or both take, the same job.
- A claimed job carries a lease (``locked_by``, ``locked_until``). The
  worker renews it with ``extend_lease``; if the worker dies, the lease
  expires and ``claim`` hands the job to another worker.
- Every state change after the claim is *fenced* on ``locked_by``: a worker
  whose lease was taken over gets ``False`` back and must stop, so it can
  never overwrite the new owner's work.
"""

from collections.abc import Sequence
from datetime import timedelta
from typing import Any
from uuid import UUID

from sqlalchemy import Row, and_, func, or_, select, text, update
from sqlalchemy.orm import Session

from neuralshelf.features.documents.models import Document, DocumentStatus, IngestionJob, JobStatus

NOTIFY_CHANNEL = "ingestion_jobs"
MAX_ERROR_LENGTH = 2000


class JobRepository:
    def __init__(self, db: Session) -> None:
        self.db = db

    def enqueue(self, *, document_id: UUID, max_attempts: int) -> IngestionJob:
        """Add a job in the caller's transaction.

        Because it shares the transaction that creates or resets the document,
        a job exists if and only if that change commits. The NOTIFY is also
        transactional: listeners are woken only after commit.
        """
        job = IngestionJob(document_id=document_id, max_attempts=max_attempts)
        self.db.add(job)
        self.db.flush()
        self.db.execute(text("SELECT pg_notify(:channel, '')"), {"channel": NOTIFY_CHANNEL})
        return job

    def get_active_for_document(self, document_id: UUID) -> IngestionJob | None:
        """The document's queued or running job; at most one exists."""
        statement = select(IngestionJob).where(
            IngestionJob.document_id == document_id,
            IngestionJob.status.in_([JobStatus.QUEUED, JobStatus.RUNNING]),
        )
        return self.db.scalar(statement)

    def has_active_job(self, document_id: UUID) -> bool:
        return self.get_active_for_document(document_id) is not None

    def get(self, job_id: UUID) -> IngestionJob | None:
        return self.db.get(IngestionJob, job_id)

    def list_with_documents(
        self, *, status: JobStatus | None, limit: int, offset: int
    ) -> tuple[Sequence[Row], int]:
        """Jobs, newest first, with their document's owner and filename (admin view)."""
        filters = [IngestionJob.status == status] if status else []
        statement = (
            select(IngestionJob, Document.user_id, Document.filename)
            .join(Document, Document.id == IngestionJob.document_id)
            .where(*filters)
            .order_by(IngestionJob.created_at.desc(), IngestionJob.id)
            .limit(limit)
            .offset(offset)
        )
        total = self.db.scalar(select(func.count()).select_from(IngestionJob).where(*filters))
        return self.db.execute(statement).all(), total or 0

    def stats(self) -> dict[str, Any]:
        """Queue health: counts per status, backlog age and stuck jobs."""
        counts = dict(
            self.db.execute(
                select(IngestionJob.status, func.count()).group_by(IngestionJob.status)
            ).all()
        )
        oldest_due = self.db.scalar(
            select(func.extract("epoch", func.now() - func.min(IngestionJob.available_at))).where(
                IngestionJob.status == JobStatus.QUEUED,
                IngestionJob.available_at <= func.now(),
            )
        )
        expired_leases = self.db.scalar(
            select(func.count())
            .select_from(IngestionJob)
            .where(
                IngestionJob.status == JobStatus.RUNNING,
                IngestionJob.locked_until < func.now(),
            )
        )
        return {
            "counts": {status.value: counts.get(status.value, 0) for status in JobStatus},
            "oldest_due_job_age_seconds": round(float(oldest_due or 0), 1),
            "running_with_expired_lease": expired_leases or 0,
        }

    def failed_document_ids_without_active_job(self, *, limit: int) -> list[UUID]:
        """Documents whose latest ingestion failed and that aren't queued again yet."""
        active = select(IngestionJob.id).where(
            IngestionJob.document_id == Document.id,
            IngestionJob.status.in_([JobStatus.QUEUED, JobStatus.RUNNING]),
        )
        statement = (
            select(Document.id)
            .where(Document.status == DocumentStatus.FAILED, ~active.exists())
            .order_by(Document.updated_at.desc().nulls_last(), Document.id)
            .limit(limit)
        )
        return list(self.db.scalars(statement).all())

    def claim(self, *, worker_id: str, lease_seconds: int) -> IngestionJob | None:
        """Atomically take the oldest due job, or one whose lease has expired."""
        now = func.now()
        candidate = (
            select(IngestionJob.id)
            .where(
                or_(
                    and_(
                        IngestionJob.status == JobStatus.QUEUED,
                        IngestionJob.available_at <= now,
                    ),
                    and_(
                        IngestionJob.status == JobStatus.RUNNING,
                        IngestionJob.locked_until < now,
                    ),
                )
            )
            .order_by(IngestionJob.available_at)
            .limit(1)
            .with_for_update(skip_locked=True)
            .scalar_subquery()
        )
        statement = (
            update(IngestionJob)
            .where(IngestionJob.id == candidate)
            .values(
                status=JobStatus.RUNNING,
                attempts=IngestionJob.attempts + 1,
                locked_by=worker_id,
                locked_until=now + timedelta(seconds=lease_seconds),
                updated_at=now,
            )
            .returning(IngestionJob)
            .execution_options(synchronize_session=False)
        )
        return self.db.scalars(statement).one_or_none()

    def extend_lease(self, *, job_id: UUID, worker_id: str, lease_seconds: int) -> bool:
        return self._fenced_update(
            job_id,
            worker_id,
            locked_until=func.now() + timedelta(seconds=lease_seconds),
        )

    def mark_succeeded(self, *, job_id: UUID, worker_id: str) -> bool:
        return self._fenced_update(
            job_id,
            worker_id,
            status=JobStatus.SUCCEEDED,
            locked_by=None,
            locked_until=None,
            last_error=None,
        )

    def schedule_retry(
        self, *, job_id: UUID, worker_id: str, error: str, delay_seconds: float
    ) -> bool:
        return self._fenced_update(
            job_id,
            worker_id,
            status=JobStatus.QUEUED,
            available_at=func.now() + timedelta(seconds=delay_seconds),
            locked_by=None,
            locked_until=None,
            last_error=error[:MAX_ERROR_LENGTH],
        )

    def mark_failed(self, *, job_id: UUID, worker_id: str, error: str) -> bool:
        return self._fenced_update(
            job_id,
            worker_id,
            status=JobStatus.FAILED,
            locked_by=None,
            locked_until=None,
            last_error=error[:MAX_ERROR_LENGTH],
        )

    def _fenced_update(self, job_id: UUID, worker_id: str, **values) -> bool:
        """Apply ``values`` only while this worker still holds the job's lease.

        The UPDATE also row-locks the job until commit, so no other worker can
        reclaim it between this check and the caller's other writes.
        """
        statement = (
            update(IngestionJob)
            .where(
                IngestionJob.id == job_id,
                IngestionJob.status == JobStatus.RUNNING,
                IngestionJob.locked_by == worker_id,
            )
            .values(updated_at=func.now(), **values)
            .execution_options(synchronize_session=False)
        )
        return self.db.execute(statement).rowcount == 1
