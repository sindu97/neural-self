"""Retrieval API endpoints."""

from dataclasses import asdict
from typing import Annotated

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from neuralshelf.core.messages import Message, MessageCode
from neuralshelf.core.schemas import ApiResponse
from neuralshelf.db.session import get_db
from neuralshelf.features.auth.dependencies import get_current_user
from neuralshelf.features.retrieval.schemas import SearchRequest, SearchResult
from neuralshelf.features.retrieval.service import RetrievalService
from neuralshelf.features.users.models import User
from neuralshelf.integrations.dependencies import get_embedding_client
from neuralshelf.integrations.embeddings.ollama import EmbeddingClient

router = APIRouter(prefix="/retrieval", tags=["Retrieval"])


def get_retrieval_service(
    db: Annotated[Session, Depends(get_db)],
    embedder: Annotated[EmbeddingClient, Depends(get_embedding_client)],
) -> RetrievalService:
    return RetrievalService(db, embedder)


@router.post("/search", response_model=ApiResponse[SearchResult])
def search(
    payload: SearchRequest,
    current_user: Annotated[User, Depends(get_current_user)],
    service: Annotated[RetrievalService, Depends(get_retrieval_service)],
) -> ApiResponse[SearchResult]:
    """Search the current user's processed documents by meaning."""
    results = service.search(
        user_id=current_user.id,
        query=payload.query,
        top_k=payload.top_k,
        document_ids=payload.document_ids,
    )

    return ApiResponse[SearchResult](
        success=True,
        code=MessageCode.SUCCESS,
        message=Message.SEARCH_COMPLETED,
        data=[SearchResult(**asdict(result)) for result in results],
    )
