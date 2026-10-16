"""Common API response schemas."""

from fastapi import Query
from pydantic import BaseModel

from neuralshelf.core.constants import DEFAULT_PAGE_LIMIT, MAX_PAGE_LIMIT


class ApiResponse[T](BaseModel):
    """Consistent envelope for successful and failed API responses.

    Unparameterized ``ApiResponse`` accepts any list items; use
    ``ApiResponse[SomeSchema]`` for a typed OpenAPI contract.
    """

    success: bool
    code: str
    message: str
    data: list[T]


class PaginationMeta(BaseModel):
    """Pagination details returned alongside list data."""

    limit: int
    offset: int
    total: int


class PaginatedResponse[T](ApiResponse[T]):
    """Envelope for list endpoints, with offset pagination metadata."""

    pagination: PaginationMeta


class PaginationParams(BaseModel):
    """Validated ``limit`` and ``offset`` query parameters."""

    limit: int
    offset: int


def pagination_params(
    limit: int = Query(DEFAULT_PAGE_LIMIT, ge=1, le=MAX_PAGE_LIMIT),
    offset: int = Query(0, ge=0),
) -> PaginationParams:
    """Bounded offset-pagination query parameters."""
    return PaginationParams(limit=limit, offset=offset)
