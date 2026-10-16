"""Administrator endpoints for operating the ingestion job queue."""

from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.orm import Session

from neuralshelf.core.messages import Message, MessageCode
from neuralshelf.core.schemas import (
    ApiResponse,
    PaginatedResponse,
    PaginationMeta,
    PaginationParams,
    pagination_params,
)
from neuralshelf.db.session import get_db
from neuralshelf.features.admin.schemas import (
    BulkRetryResponse,
    IngestionJobResponse,
    JobStatsResponse,
)
from neuralshelf.features.admin.service import AdminJobService
from neuralshelf.features.auth.dependencies import require_admin
from neuralshelf.features.documents.models import JobStatus

# Every route here requires an administrator; others get 403.
router = APIRouter(
    prefix="/admin/ingestion-jobs",
    tags=["Admin"],
    dependencies=[Depends(require_admin)],
)

MAX_BULK_RETRY = 500


def get_admin_job_service(db: Annotated[Session, Depends(get_db)]) -> AdminJobService:
    """Dependency: the admin job service for this request."""
    return AdminJobService(db)


Service = Annotated[AdminJobService, Depends(get_admin_job_service)]


@router.get("", response_model=PaginatedResponse[IngestionJobResponse])
def list_jobs(
    service: Service,
    page: Annotated[PaginationParams, Depends(pagination_params)],
    job_status: Annotated[JobStatus | None, Query(alias="status")] = None,
) -> PaginatedResponse[IngestionJobResponse]:
    """List ingestion jobs, newest first; filter with ?status=failed."""
    rows, total = service.list_jobs(status=job_status, limit=page.limit, offset=page.offset)

    return PaginatedResponse[IngestionJobResponse](
        success=True,
        code=MessageCode.SUCCESS,
        message=Message.JOBS_RETRIEVED,
        data=[
            IngestionJobResponse(
                id=job.id,
                document_id=job.document_id,
                user_id=user_id,
                filename=filename,
                status=JobStatus(job.status),
                attempts=job.attempts,
                max_attempts=job.max_attempts,
                last_error=job.last_error,
                locked_by=job.locked_by,
                available_at=job.available_at,
                created_at=job.created_at,
                updated_at=job.updated_at,
            )
            for job, user_id, filename in rows
        ],
        pagination=PaginationMeta(limit=page.limit, offset=page.offset, total=total),
    )


@router.get("/stats", response_model=ApiResponse[JobStatsResponse])
def job_stats(service: Service) -> ApiResponse[JobStatsResponse]:
    """Queue health.

    Jobs per status, how long the oldest due job has waited, and running jobs
    whose worker appears to have died.
    """
    return ApiResponse[JobStatsResponse](
        success=True,
        code=MessageCode.SUCCESS,
        message=Message.JOB_STATS_RETRIEVED,
        data=[JobStatsResponse(**service.stats())],
    )


@router.post(
    "/retry-failed",
    response_model=ApiResponse[BulkRetryResponse],
    status_code=status.HTTP_202_ACCEPTED,
)
def retry_all_failed(
    service: Service,
    limit: Annotated[int, Query(ge=1, le=MAX_BULK_RETRY)] = 100,
) -> ApiResponse[BulkRetryResponse]:
    """Requeue failed documents, e.g. after fixing an outage that made them fail."""
    document_ids = service.retry_all_failed(limit=limit)

    return ApiResponse[BulkRetryResponse](
        success=True,
        code=MessageCode.SUCCESS,
        message=Message.FAILED_JOBS_REQUEUED,
        data=[BulkRetryResponse(requeued=len(document_ids), document_ids=document_ids)],
    )


@router.post(
    "/{job_id}/retry",
    response_model=ApiResponse[dict],
    status_code=status.HTTP_202_ACCEPTED,
)
def retry_job(job_id: UUID, service: Service) -> ApiResponse[dict]:
    """Queue a new attempt for a failed job's document. The failed job stays as history."""
    new_job = service.retry_job(job_id)

    return ApiResponse[dict](
        success=True,
        code=MessageCode.SUCCESS,
        message=Message.JOB_RETRY_QUEUED,
        data=[{"job_id": new_job.id, "document_id": new_job.document_id}],
    )
