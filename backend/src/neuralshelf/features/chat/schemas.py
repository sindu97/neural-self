"""Request and response schemas for conversations and messages."""

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, field_validator

from neuralshelf.core.constants import (
    RETRIEVAL_DEFAULT_TOP_K,
    RETRIEVAL_MAX_DOCUMENT_FILTERS,
    RETRIEVAL_MAX_TOP_K,
)
from neuralshelf.features.chat.models import ChatMessage, MessageRole


class ConversationCreateRequest(BaseModel):
    title: str | None = Field(default=None, max_length=200)

    @field_validator("title")
    @classmethod
    def normalize_title(cls, value: str | None) -> str | None:
        if value is None:
            return None
        return " ".join(value.split()) or None


class ConversationResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    title: str | None
    created_at: datetime
    updated_at: datetime


class MessageCreateRequest(BaseModel):
    content: str = Field(min_length=1, max_length=4000)
    top_k: int = Field(default=RETRIEVAL_DEFAULT_TOP_K, ge=1, le=RETRIEVAL_MAX_TOP_K)
    document_ids: list[UUID] = Field(
        default_factory=list,
        max_length=RETRIEVAL_MAX_DOCUMENT_FILTERS,
        description="Answer only from these documents; empty uses all of them.",
    )

    @field_validator("content")
    @classmethod
    def strip_content(cls, value: str) -> str:
        value = value.strip()
        if not value:
            raise ValueError("Must not be blank")
        return value


class Citation(BaseModel):
    """A source passage; ``number`` matches the [n] markers in the answer."""

    number: int
    document_id: UUID
    filename: str
    page_number: int | None
    chunk_index: int
    score: float
    excerpt: str


class MessageResponse(BaseModel):
    id: UUID
    conversation_id: UUID
    role: MessageRole
    content: str
    created_at: datetime
    citations: list[Citation] = []

    @classmethod
    def from_model(cls, message: ChatMessage) -> "MessageResponse":
        metadata = message.message_metadata or {}
        return cls(
            id=message.id,
            conversation_id=message.conversation_id,
            role=MessageRole(message.role),
            content=message.content,
            created_at=message.created_at,
            citations=[Citation(**citation) for citation in metadata.get("citations", [])],
        )


class ExchangeResponse(BaseModel):
    """The saved question and its generated answer."""

    user_message: MessageResponse
    assistant_message: MessageResponse
