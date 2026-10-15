"""Administrator endpoints for the ingestion job queue."""

import pytest
from sqlalchemy import select

from neuralshelf import cli
from neuralshelf.db.seeders.sample_pdf import make_pdf
from neuralshelf.features.documents.models import IngestionJob, JobStatus
from neuralshelf.features.users.models import User

pytestmark = pytest.mark.integration

API = "/api/v1"
JOBS = f"{API}/admin/ingestion-jobs"


@pytest.fixture
def admin_headers(auth_headers, session_factory):
    headers = auth_headers("admin@example.com")
    with session_factory() as db:
        db.scalar(select(User).where(User.email == "admin@example.com")).is_admin = True
        db.commit()
    return headers


@pytest.fixture
def user_headers(auth_headers):
    return auth_headers("user@example.com")


@pytest.fixture
def failed_document(client, user_headers, worker):
    """A document whose ingestion failed (its PDF has no text)."""
    response = client.post(
        f"{API}/documents",
        headers=user_headers,
        files={"file": ("empty.pdf", make_pdf([""]), "application/pdf")},
    )
    worker.run_until_idle()
    return response.json()["data"][0]


def test_admin_endpoints_require_an_administrator(client, user_headers) -> None:
    assert client.get(JOBS).status_code == 401
    response = client.get(JOBS, headers=user_headers)
    assert response.status_code == 403
    assert response.json()["code"] == "FORBIDDEN"
    assert client.post(f"{JOBS}/retry-failed", headers=user_headers).status_code == 403


def test_list_failed_jobs_with_details(client, admin_headers, failed_document) -> None:
    response = client.get(f"{JOBS}?status=failed", headers=admin_headers)

    assert response.status_code == 200
    body = response.json()
    assert body["pagination"]["total"] == 1
    job = body["data"][0]
    assert job["document_id"] == failed_document["id"]
    assert job["filename"] == "empty.pdf"
    assert job["status"] == "failed"
    assert job["attempts"] == 1
    assert "No extractable text" in job["last_error"]

    assert client.get(f"{JOBS}?status=queued", headers=admin_headers).json()["data"] == []
    assert client.get(f"{JOBS}?status=bogus", headers=admin_headers).status_code == 422


def test_stats_report_queue_health(client, admin_headers, failed_document) -> None:
    stats = client.get(f"{JOBS}/stats", headers=admin_headers).json()["data"][0]

    assert stats["counts"] == {"queued": 0, "running": 0, "succeeded": 0, "failed": 1}
    assert stats["oldest_due_job_age_seconds"] == 0
    assert stats["running_with_expired_lease"] == 0


def test_retry_failed_job_queues_a_new_attempt(
    client, admin_headers, user_headers, failed_document, session_factory
) -> None:
    failed_job = client.get(f"{JOBS}?status=failed", headers=admin_headers).json()["data"][0]

    response = client.post(f"{JOBS}/{failed_job['id']}/retry", headers=admin_headers)

    assert response.status_code == 202
    new_job_id = response.json()["data"][0]["job_id"]
    assert new_job_id != failed_job["id"]
    with session_factory() as db:
        statuses = {str(j.id): j.status for j in db.scalars(select(IngestionJob))}
    assert statuses == {failed_job["id"]: JobStatus.FAILED, new_job_id: JobStatus.QUEUED}
    document = client.get(f"{API}/documents/{failed_document['id']}", headers=user_headers)
    assert document.json()["data"][0]["status"] == "uploaded"

    # The failed job can't be retried twice while the new attempt is pending.
    again = client.post(f"{JOBS}/{failed_job['id']}/retry", headers=admin_headers)
    assert again.status_code == 409
    assert again.json()["code"] == "DOCUMENT_BUSY"


def test_retry_rejects_unknown_and_non_failed_jobs(
    client, admin_headers, user_headers, worker
) -> None:
    unknown = client.post(
        f"{JOBS}/00000000-0000-0000-0000-000000000000/retry", headers=admin_headers
    )
    assert unknown.status_code == 404
    assert unknown.json()["code"] == "JOB_NOT_FOUND"

    client.post(
        f"{API}/documents",
        headers=user_headers,
        files={"file": ("ok.pdf", make_pdf(["Some real text here"]), "application/pdf")},
    )
    worker.run_until_idle()
    succeeded = client.get(f"{JOBS}?status=succeeded", headers=admin_headers).json()["data"][0]

    response = client.post(f"{JOBS}/{succeeded['id']}/retry", headers=admin_headers)
    assert response.status_code == 409
    assert response.json()["code"] == "JOB_NOT_FAILED"


def test_bulk_retry_requeues_every_failed_document(
    client, admin_headers, user_headers, failed_document
) -> None:
    second = client.post(
        f"{API}/documents",
        headers=user_headers,
        files={"file": ("empty2.pdf", make_pdf([""]), "application/pdf")},
    ).json()["data"][0]
    # Second one is still queued, so only the first is eligible.

    response = client.post(f"{JOBS}/retry-failed", headers=admin_headers)

    assert response.status_code == 202
    result = response.json()["data"][0]
    assert result == {"requeued": 1, "document_ids": [failed_document["id"]]}
    assert second["id"] not in result["document_ids"]

    repeat = client.post(f"{JOBS}/retry-failed", headers=admin_headers).json()["data"][0]
    assert repeat["requeued"] == 0


def test_cli_promotes_and_demotes_admins(
    client, auth_headers, session_factory, monkeypatch, capsys
) -> None:
    auth_headers("ops@example.com")
    monkeypatch.setattr(cli, "SessionLocal", session_factory)

    assert cli.main(["promote-admin", "OPS@example.com"]) == 0
    with session_factory() as db:
        assert db.scalar(select(User.is_admin).where(User.email == "ops@example.com")) is True

    assert cli.main(["demote-admin", "ops@example.com"]) == 0
    assert cli.main(["promote-admin", "missing@example.com"]) == 1
    assert "No user" in capsys.readouterr().err
