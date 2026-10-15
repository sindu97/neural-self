"""Response schemas for documents."""

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict

from neuralshelf.features.documents.models import DocumentStatus


class DocumentResponse(BaseModel):
    """Document metadata and ingestion status returned by the API."""

    model_config = ConfigDict(from_attributes=True)

    id: UUID
    filename: str
    content_type: str | None
    file_size_bytes: int | None
    status: DocumentStatus
    error_message: str | None
    created_at: datetime
    updated_at: datetime | None
