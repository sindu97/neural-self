"""Ingestion worker process.

Run with:  python -m neuralshelf.workers.ingestion_worker

Loop: claim a job -> process it while a heartbeat renews its lease -> repeat.
When the queue is empty, sleep until a NOTIFY arrives (instant wake-up on new
uploads) or the poll interval passes (which also catches retries becoming
due and leases expiring). Run several copies to scale out; SKIP LOCKED keeps
them from taking the same job.

On SIGTERM/SIGINT the worker finishes its current job, then exits. If it is
killed outright, the job's lease expires and another worker resumes it.
"""

import logging
import os
import signal
import socket
import threading
import uuid
from types import FrameType
from uuid import UUID

import psycopg
from sqlalchemy import make_url
from sqlalchemy.orm import Session, sessionmaker

from neuralshelf.core.config import get_settings
from neuralshelf.core.logging import configure_logging, request_id_var
from neuralshelf.db import model_registry  # noqa: F401  (registers all models)
from neuralshelf.db.session import SessionLocal
from neuralshelf.features.documents.ingestion import JobContext, run_ingestion_job
from neuralshelf.features.documents.job_repository import NOTIFY_CHANNEL, JobRepository
from neuralshelf.features.documents.storage import get_file_storage
from neuralshelf.integrations.dependencies import get_embedding_client

logger = logging.getLogger(__name__)


class LeaseHeartbeat:
    """Renew a job's lease on a background thread while the job runs.

    Renewal is independent of how long any single step (parsing, embedding)
    takes. If renewal reports the lease was lost, the beat stops; the job's
    final fenced write will then fail and the worker discards its result.
    """

    def __init__(
        self,
        *,
        session_factory: sessionmaker[Session],
        job_id: UUID,
        worker_id: str,
        lease_seconds: int,
        interval_seconds: float,
    ) -> None:
        self.session_factory = session_factory
        self.job_id = job_id
        self.worker_id = worker_id
        self.lease_seconds = lease_seconds
        self.interval_seconds = interval_seconds
        self._stop = threading.Event()
        self._thread = threading.Thread(target=self._run, name=f"heartbeat-{job_id}", daemon=True)

    def __enter__(self) -> "LeaseHeartbeat":
        self._thread.start()
        return self

    def __exit__(self, *_: object) -> None:
        self._stop.set()
        self._thread.join()

    def _run(self) -> None:
        while not self._stop.wait(self.interval_seconds):
            try:
                with self.session_factory() as db:
                    renewed = JobRepository(db).extend_lease(
                        job_id=self.job_id,
                        worker_id=self.worker_id,
                        lease_seconds=self.lease_seconds,
                    )
                    db.commit()
                if not renewed:
                    logger.warning("Lease for job %s was lost.", self.job_id)
                    return
            except Exception:
                # Keep trying; the lease has slack for a few missed beats.
                logger.exception("Heartbeat for job %s failed.", self.job_id)


class IngestionWorker:
    def __init__(self, context: JobContext) -> None:
        self.context = context

    def run_once(self) -> bool:
        """Claim and process one job. Returns False when no job was available."""
        settings = get_settings()

        with self.context.session_factory() as db:
            job = JobRepository(db).claim(
                worker_id=self.context.worker_id,
                lease_seconds=settings.job_lease_seconds,
            )
            db.commit()

        if job is None:
            return False

        # Tag every log line of this job, so its whole history can be found.
        log_context = request_id_var.set(f"job:{job.id}")
        try:
            logger.info(
                "Claimed job %s for document %s (attempt %d/%d).",
                job.id,
                job.document_id,
                job.attempts,
                job.max_attempts,
            )
            with LeaseHeartbeat(
                session_factory=self.context.session_factory,
                job_id=job.id,
                worker_id=self.context.worker_id,
                lease_seconds=settings.job_lease_seconds,
                interval_seconds=settings.job_heartbeat_seconds,
            ):
                run_ingestion_job(job, self.context)
        finally:
            request_id_var.reset(log_context)
        return True

    def run_until_idle(self) -> int:
        """Process jobs until none are due. Returns how many were processed."""
        processed = 0
        while self.run_once():
            processed += 1
        return processed


class JobNotificationListener:
    """Wait for NOTIFYs on the job channel, reconnecting after failures."""

    def __init__(self, conninfo: str) -> None:
        self.conninfo = conninfo
        self._connection: psycopg.Connection | None = None

    def wait(self, timeout: float, stop: threading.Event) -> None:
        try:
            if self._connection is None or self._connection.closed:
                self._connection = psycopg.connect(self.conninfo, autocommit=True)
                self._connection.execute(f"LISTEN {NOTIFY_CHANNEL}")
            for _ in self._connection.notifies(timeout=timeout, stop_after=1):
                pass
        except psycopg.Error:
            logger.warning("Job notification listener unavailable; polling instead.")
            self.close()
            stop.wait(timeout)

    def close(self) -> None:
        if self._connection is not None:
            self._connection.close()
            self._connection = None


def build_worker_id() -> str:
    return f"{socket.gethostname()}:{os.getpid()}:{uuid.uuid4().hex[:8]}"


def main() -> None:
    configure_logging()
    settings = get_settings()

    worker_id = build_worker_id()
    worker = IngestionWorker(
        JobContext(
            session_factory=SessionLocal,
            storage=get_file_storage(),
            embedder=get_embedding_client(),
            worker_id=worker_id,
        )
    )

    stop = threading.Event()

    def request_stop(signum: int, _: FrameType | None) -> None:
        signal_name = signal.Signals(signum).name
        logger.info("Received %s; finishing current job, then exiting.", signal_name)
        stop.set()

    signal.signal(signal.SIGTERM, request_stop)
    signal.signal(signal.SIGINT, request_stop)

    # psycopg needs a plain libpq URL, not SQLAlchemy's "postgresql+psycopg://".
    conninfo = (
        make_url(settings.database_url.get_secret_value())
        .set(drivername="postgresql")
        .render_as_string(hide_password=False)
    )
    listener = JobNotificationListener(conninfo)
    logger.info("Ingestion worker %s started.", worker_id)

    try:
        while not stop.is_set():
            try:
                if worker.run_once():
                    continue
            except Exception:
                # e.g. database unreachable while claiming; back off and retry.
                logger.exception("Worker loop error.")
                stop.wait(settings.worker_poll_interval_seconds)
                continue
            listener.wait(settings.worker_poll_interval_seconds, stop)
    finally:
        listener.close()
        logger.info("Ingestion worker %s stopped.", worker_id)


if __name__ == "__main__":
    main()
