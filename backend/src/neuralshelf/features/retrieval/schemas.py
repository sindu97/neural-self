"""Request and response schemas for retrieval."""

from uuid import UUID

from pydantic import BaseModel, Field, field_validator

from neuralshelf.core.constants import (
    RETRIEVAL_DEFAULT_TOP_K,
    RETRIEVAL_MAX_DOCUMENT_FILTERS,
    RETRIEVAL_MAX_TOP_K,
)


def _strip_required(value: str) -> str:
    value = value.strip()
    if not value:
        raise ValueError("Must not be blank")
    return value


class SearchRequest(BaseModel):
    """Body of ``POST /retrieval/search``."""

    query: str = Field(min_length=1, max_length=2000)
    top_k: int = Field(default=RETRIEVAL_DEFAULT_TOP_K, ge=1, le=RETRIEVAL_MAX_TOP_K)
    document_ids: list[UUID] = Field(
        default_factory=list,
        max_length=RETRIEVAL_MAX_DOCUMENT_FILTERS,
        description="Restrict the search to these documents; empty searches all of them.",
    )

    _strip_query = field_validator("query")(_strip_required)


class SearchResult(BaseModel):
    """One matching passage, where it came from, and how similar it is."""

    chunk_id: int
    document_id: UUID
    filename: str
    chunk_index: int
    page_number: int | None
    content: str
    score: float
