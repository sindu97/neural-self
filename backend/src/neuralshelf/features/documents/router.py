"""Document upload and management API endpoints."""

from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, File, UploadFile, status
from sqlalchemy.orm import Session

from neuralshelf.core.config import get_settings
from neuralshelf.core.messages import Message, MessageCode
from neuralshelf.core.schemas import (
    ApiResponse,
    PaginatedResponse,
    PaginationMeta,
    PaginationParams,
    pagination_params,
)
from neuralshelf.db.session import get_db
from neuralshelf.features.auth.dependencies import get_current_user
from neuralshelf.features.documents.schemas import DocumentResponse
from neuralshelf.features.documents.service import DocumentService
from neuralshelf.features.documents.storage import LocalFileStorage, get_file_storage
from neuralshelf.features.users.models import User

router = APIRouter(prefix="/documents", tags=["Documents"])

CurrentUser = Annotated[User, Depends(get_current_user)]


def get_document_service(
    db: Annotated[Session, Depends(get_db)],
    storage: Annotated[LocalFileStorage, Depends(get_file_storage)],
) -> DocumentService:
    return DocumentService(db, storage)


Service = Annotated[DocumentService, Depends(get_document_service)]


@router.post(
    "",
    response_model=ApiResponse[DocumentResponse],
    status_code=status.HTTP_202_ACCEPTED,
)
def upload_document(
    current_user: CurrentUser,
    service: Service,
    file: Annotated[UploadFile, File(description="PDF file to upload")],
) -> ApiResponse[DocumentResponse]:
    """Upload a PDF and queue it for ingestion; poll the document for its status."""
    # Read one byte past the limit so oversized files are detected without
    # loading arbitrarily large uploads into memory.
    data = file.file.read(get_settings().max_upload_size_bytes + 1)
    document = service.upload(
        user_id=current_user.id,
        filename=file.filename,
        content_type=file.content_type,
        data=data,
    )

    return ApiResponse[DocumentResponse](
        success=True,
        code=MessageCode.SUCCESS,
        message=Message.DOCUMENT_UPLOADED,
        data=[DocumentResponse.model_validate(document)],
    )


@router.get("", response_model=PaginatedResponse[DocumentResponse])
def list_documents(
    current_user: CurrentUser,
    service: Service,
    page: Annotated[PaginationParams, Depends(pagination_params)],
) -> PaginatedResponse[DocumentResponse]:
    """List the current user's documents, newest first."""
    documents, total = service.list(user_id=current_user.id, limit=page.limit, offset=page.offset)

    return PaginatedResponse[DocumentResponse](
        success=True,
        code=MessageCode.SUCCESS,
        message=Message.DOCUMENTS_RETRIEVED,
        data=[DocumentResponse.model_validate(document) for document in documents],
        pagination=PaginationMeta(limit=page.limit, offset=page.offset, total=total),
    )


@router.get("/{document_id}", response_model=ApiResponse[DocumentResponse])
def get_document(
    document_id: UUID,
    current_user: CurrentUser,
    service: Service,
) -> ApiResponse[DocumentResponse]:
    """Get document metadata and ingestion status."""
    document = service.get(user_id=current_user.id, document_id=document_id)

    return ApiResponse[DocumentResponse](
        success=True,
        code=MessageCode.SUCCESS,
        message=Message.DOCUMENT_RETRIEVED,
        data=[DocumentResponse.model_validate(document)],
    )


@router.delete("/{document_id}", response_model=ApiResponse)
def delete_document(
    document_id: UUID,
    current_user: CurrentUser,
    service: Service,
) -> ApiResponse:
    """Delete a document, its chunks, and its stored file."""
    service.delete(user_id=current_user.id, document_id=document_id)

    return ApiResponse(
        success=True,
        code=MessageCode.SUCCESS,
        message=Message.DOCUMENT_DELETED,
        data=[],
    )


@router.post(
    "/{document_id}/reprocess",
    response_model=ApiResponse[DocumentResponse],
    status_code=status.HTTP_202_ACCEPTED,
)
def reprocess_document(
    document_id: UUID,
    current_user: CurrentUser,
    service: Service,
) -> ApiResponse[DocumentResponse]:
    """Queue ingestion again for a failed or completed document."""
    document = service.reprocess(user_id=current_user.id, document_id=document_id)

    return ApiResponse[DocumentResponse](
        success=True,
        code=MessageCode.SUCCESS,
        message=Message.DOCUMENT_REPROCESSING,
        data=[DocumentResponse.model_validate(document)],
    )
