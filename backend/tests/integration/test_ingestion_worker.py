"""Job-queue guarantees: transactional enqueue, crash recovery, retries,
permanent failures, fencing and safe concurrent claiming."""

import pytest
from sqlalchemy import func, select, update

from neuralshelf.core.exceptions import EmbeddingServiceError
from neuralshelf.core.messages import Message
from neuralshelf.features.documents.job_repository import JobRepository
from neuralshelf.features.documents.models import Chunk, Document, IngestionJob, JobStatus
from tests.pdf_factory import make_pdf

pytestmark = pytest.mark.integration

API = "/api/v1"
TEXT = "Photosynthesis lets plants convert sunlight into chemical energy."


class FlakyEmbedder:
    """Fails the first ``failures`` calls, then delegates to a working embedder."""

    def __init__(self, inner, failures: int) -> None:
        self.inner = inner
        self.failures = failures
        self.calls = 0

    def embed_documents(self, texts):
        self.calls += 1
        if self.calls <= self.failures:
            raise EmbeddingServiceError()
        return self.inner.embed_documents(texts)

    def embed_query(self, text):
        return self.inner.embed_query(text)


@pytest.fixture
def headers(auth_headers):
    return auth_headers("worker-test@example.com")


@pytest.fixture
def upload(client, headers):
    def _upload(pages=(TEXT,)) -> str:
        response = client.post(
            f"{API}/documents",
            headers=headers,
            files={"file": ("doc.pdf", make_pdf(list(pages)), "application/pdf")},
        )
        assert response.status_code == 202, response.text
        return response.json()["data"][0]["id"]

    return _upload


def get_job(session_factory, document_id) -> IngestionJob:
    with session_factory() as db:
        return db.scalars(
            select(IngestionJob)
            .where(IngestionJob.document_id == document_id)
            .order_by(IngestionJob.created_at.desc())
        ).first()


def get_document(session_factory, document_id) -> Document:
    with session_factory() as db:
        return db.get(Document, document_id)


def make_due(session_factory, **fields) -> None:
    """Fast-forward time: make retries due and leases expired."""
    with session_factory() as db:
        db.execute(update(IngestionJob).values(**fields))
        db.commit()


def test_upload_enqueues_a_job_in_the_same_transaction(upload, session_factory) -> None:
    document_id = upload()

    job = get_job(session_factory, document_id)
    assert job.status == JobStatus.QUEUED
    assert job.attempts == 0
    assert get_document(session_factory, document_id).status == "uploaded"


def test_worker_processes_queued_job(upload, worker, session_factory) -> None:
    document_id = upload()

    assert worker.run_once() is True
    assert worker.run_once() is False  # queue drained

    job = get_job(session_factory, document_id)
    assert job.status == JobStatus.SUCCEEDED
    assert job.locked_by is None
    assert get_document(session_factory, document_id).status == "completed"


def test_crashed_worker_job_is_resumed_after_lease_expires(
    upload, make_worker, session_factory
) -> None:
    document_id = upload()

    # Worker A claims the job, then "crashes" without finishing or releasing it.
    with session_factory() as db:
        claimed = JobRepository(db).claim(worker_id="worker-a", lease_seconds=60)
        db.commit()
    assert claimed is not None

    worker_b = make_worker("worker-b")
    assert worker_b.run_once() is False  # lease still valid: not stolen

    make_due(session_factory, locked_until=func.now())
    assert worker_b.run_once() is True

    job = get_job(session_factory, document_id)
    assert job.status == JobStatus.SUCCEEDED
    assert job.attempts == 2
    assert get_document(session_factory, document_id).status == "completed"


def test_transient_failure_is_retried_with_backoff(
    upload, make_worker, embedder, session_factory
) -> None:
    document_id = upload()
    flaky = FlakyEmbedder(embedder, failures=1)
    worker = make_worker(embedder_override=flaky)

    assert worker.run_once() is True
    job = get_job(session_factory, document_id)
    assert job.status == JobStatus.QUEUED
    assert "EmbeddingServiceError" in job.last_error
    assert get_document(session_factory, document_id).status == "processing"

    assert worker.run_once() is False  # backoff: not due yet

    make_due(session_factory, available_at=func.now())
    assert worker.run_once() is True

    job = get_job(session_factory, document_id)
    assert job.status == JobStatus.SUCCEEDED
    assert job.attempts == 2
    assert get_document(session_factory, document_id).status == "completed"


def test_job_fails_for_good_after_max_attempts(
    upload, make_worker, embedder, session_factory
) -> None:
    document_id = upload()
    worker = make_worker(embedder_override=FlakyEmbedder(embedder, failures=10_000))
    make_due(session_factory, max_attempts=3)

    for _ in range(3):
        make_due(session_factory, available_at=func.now())
        assert worker.run_once() is True

    job = get_job(session_factory, document_id)
    assert job.status == JobStatus.FAILED
    assert job.attempts == 3
    document = get_document(session_factory, document_id)
    assert document.status == "failed"
    assert document.error_message == Message.EMBEDDING_SERVICE_UNAVAILABLE


def test_permanent_failure_is_not_retried(upload, worker, session_factory) -> None:
    document_id = upload(pages=("",))

    worker.run_once()

    job = get_job(session_factory, document_id)
    assert job.status == JobStatus.FAILED
    assert job.attempts == 1
    assert get_document(session_factory, document_id).error_message == Message.INGESTION_NO_TEXT


def test_job_that_keeps_crashing_its_worker_is_given_up(
    upload, worker, session_factory
) -> None:
    document_id = upload()
    make_due(session_factory, max_attempts=2)

    # Two claims whose workers "die" mid-job.
    for name in ("crash-1", "crash-2"):
        with session_factory() as db:
            JobRepository(db).claim(worker_id=name, lease_seconds=60)
            db.commit()
        make_due(session_factory, locked_until=func.now())

    assert worker.run_once() is True  # third claim exceeds max_attempts

    assert get_job(session_factory, document_id).status == JobStatus.FAILED
    assert get_document(session_factory, document_id).status == "failed"
    with session_factory() as db:
        assert db.scalar(select(func.count()).select_from(Chunk)) == 0


def test_worker_that_lost_its_lease_cannot_complete_the_job(upload, session_factory) -> None:
    upload()

    with session_factory() as db:
        job = JobRepository(db).claim(worker_id="slow-worker", lease_seconds=60)
        db.commit()
    make_due(session_factory, locked_until=func.now())
    with session_factory() as db:
        assert JobRepository(db).claim(worker_id="new-owner", lease_seconds=60) is not None
        db.commit()

    with session_factory() as db:
        repository = JobRepository(db)
        assert repository.mark_succeeded(job_id=job.id, worker_id="slow-worker") is False
        assert not repository.extend_lease(job_id=job.id, worker_id="slow-worker", lease_seconds=60)
        assert repository.mark_succeeded(job_id=job.id, worker_id="new-owner") is True
        db.commit()


def test_concurrent_claims_never_take_the_same_job(upload, session_factory) -> None:
    upload()
    upload()

    # Two open transactions claim at the same time; SKIP LOCKED gives each a different job.
    with session_factory() as db_a, session_factory() as db_b:
        job_a = JobRepository(db_a).claim(worker_id="a", lease_seconds=60)
        job_b = JobRepository(db_b).claim(worker_id="b", lease_seconds=60)
        job_c = JobRepository(db_b).claim(worker_id="b", lease_seconds=60)
        assert job_a is not None and job_b is not None
        assert job_a.id != job_b.id
        assert job_c is None
        db_a.commit()
        db_b.commit()


def test_reprocess_is_rejected_while_a_job_is_active(client, headers, upload) -> None:
    document_id = upload()

    response = client.post(f"{API}/documents/{document_id}/reprocess", headers=headers)

    assert response.status_code == 409
    assert response.json()["code"] == "DOCUMENT_BUSY"


def test_deleting_a_document_removes_its_queued_job(
    client, headers, upload, worker, session_factory
) -> None:
    document_id = upload()

    assert client.delete(f"{API}/documents/{document_id}", headers=headers).status_code == 200

    assert get_job(session_factory, document_id) is None
    assert worker.run_once() is False
