"""Conversation and message API endpoints."""

import json
from collections.abc import Iterator
from typing import Annotated, Any
from uuid import UUID

from fastapi import APIRouter, Depends, status
from fastapi.encoders import jsonable_encoder
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session, sessionmaker

from neuralshelf.core.messages import Message, MessageCode
from neuralshelf.core.schemas import (
    ApiResponse,
    PaginatedResponse,
    PaginationMeta,
    PaginationParams,
    pagination_params,
)
from neuralshelf.db.session import get_db, get_session_factory
from neuralshelf.features.auth.dependencies import get_current_user
from neuralshelf.features.chat.schemas import (
    ConversationCreateRequest,
    ConversationResponse,
    ExchangeResponse,
    MessageCreateRequest,
    MessageResponse,
)
from neuralshelf.features.chat.service import ChatService, stream_answer
from neuralshelf.features.retrieval.router import get_retrieval_service
from neuralshelf.features.retrieval.service import RetrievalService
from neuralshelf.features.users.models import User
from neuralshelf.integrations.dependencies import get_chat_client
from neuralshelf.integrations.llm.ollama import ChatClient

router = APIRouter(prefix="/conversations", tags=["Conversations"])

CurrentUser = Annotated[User, Depends(get_current_user)]
Page = Annotated[PaginationParams, Depends(pagination_params)]


def get_chat_service(
    db: Annotated[Session, Depends(get_db)],
    retrieval: Annotated[RetrievalService, Depends(get_retrieval_service)],
    llm: Annotated[ChatClient, Depends(get_chat_client)],
) -> ChatService:
    """Dependency: the chat service for this request."""
    return ChatService(db, retrieval, llm)


Service = Annotated[ChatService, Depends(get_chat_service)]


@router.post(
    "",
    response_model=ApiResponse[ConversationResponse],
    status_code=status.HTTP_201_CREATED,
)
def create_conversation(
    current_user: CurrentUser,
    service: Service,
    payload: ConversationCreateRequest | None = None,
) -> ApiResponse[ConversationResponse]:
    """Create a conversation. Without a title, the first question becomes the title."""
    conversation = service.create_conversation(
        user_id=current_user.id,
        title=payload.title if payload else None,
    )

    return ApiResponse[ConversationResponse](
        success=True,
        code=MessageCode.SUCCESS,
        message=Message.CONVERSATION_CREATED,
        data=[ConversationResponse.model_validate(conversation)],
    )


@router.get("", response_model=PaginatedResponse[ConversationResponse])
def list_conversations(
    current_user: CurrentUser,
    service: Service,
    page: Page,
) -> PaginatedResponse[ConversationResponse]:
    """List the current user's conversations, most recently active first."""
    conversations, total = service.list_conversations(
        user_id=current_user.id, limit=page.limit, offset=page.offset
    )

    return PaginatedResponse[ConversationResponse](
        success=True,
        code=MessageCode.SUCCESS,
        message=Message.CONVERSATIONS_RETRIEVED,
        data=[ConversationResponse.model_validate(c) for c in conversations],
        pagination=PaginationMeta(limit=page.limit, offset=page.offset, total=total),
    )


@router.get("/{conversation_id}", response_model=ApiResponse[ConversationResponse])
def get_conversation(
    conversation_id: UUID,
    current_user: CurrentUser,
    service: Service,
) -> ApiResponse[ConversationResponse]:
    """Get a conversation's details."""
    conversation = service.get_conversation(
        user_id=current_user.id, conversation_id=conversation_id
    )

    return ApiResponse[ConversationResponse](
        success=True,
        code=MessageCode.SUCCESS,
        message=Message.CONVERSATION_RETRIEVED,
        data=[ConversationResponse.model_validate(conversation)],
    )


@router.delete("/{conversation_id}", response_model=ApiResponse)
def delete_conversation(
    conversation_id: UUID,
    current_user: CurrentUser,
    service: Service,
) -> ApiResponse:
    """Delete a conversation and all its messages."""
    service.delete_conversation(user_id=current_user.id, conversation_id=conversation_id)

    return ApiResponse(
        success=True,
        code=MessageCode.SUCCESS,
        message=Message.CONVERSATION_DELETED,
        data=[],
    )


@router.get(
    "/{conversation_id}/messages",
    response_model=PaginatedResponse[MessageResponse],
)
def list_messages(
    conversation_id: UUID,
    current_user: CurrentUser,
    service: Service,
    page: Page,
) -> PaginatedResponse[MessageResponse]:
    """Conversation history, oldest first."""
    messages, total = service.list_messages(
        user_id=current_user.id,
        conversation_id=conversation_id,
        limit=page.limit,
        offset=page.offset,
    )

    return PaginatedResponse[MessageResponse](
        success=True,
        code=MessageCode.SUCCESS,
        message=Message.MESSAGES_RETRIEVED,
        data=[MessageResponse.from_model(m) for m in messages],
        pagination=PaginationMeta(limit=page.limit, offset=page.offset, total=total),
    )


@router.post(
    "/{conversation_id}/messages",
    response_model=ApiResponse[ExchangeResponse],
    status_code=status.HTTP_201_CREATED,
)
def send_message(
    conversation_id: UUID,
    payload: MessageCreateRequest,
    current_user: CurrentUser,
    service: Service,
) -> ApiResponse[ExchangeResponse]:
    """Ask a question; returns the complete answer with citations (not streamed)."""
    user_message, assistant_message = service.send_message(
        user_id=current_user.id,
        conversation_id=conversation_id,
        content=payload.content,
        top_k=payload.top_k,
        document_ids=payload.document_ids,
    )

    return ApiResponse[ExchangeResponse](
        success=True,
        code=MessageCode.SUCCESS,
        message=Message.MESSAGE_ANSWERED,
        data=[
            ExchangeResponse(
                user_message=MessageResponse.from_model(user_message),
                assistant_message=MessageResponse.from_model(assistant_message),
            )
        ],
    )


def _sse(event: str, data: Any) -> str:
    """Format one Server-Sent Event."""
    return f"event: {event}\ndata: {json.dumps(jsonable_encoder(data))}\n\n"


@router.post(
    "/{conversation_id}/messages/stream",
    response_class=StreamingResponse,
    responses={
        200: {
            "description": (
                "Server-Sent Events: `start` (citations), `token` (answer fragments), "
                "then `done` (saved messages, same shape as the non-streaming endpoint) "
                "or `error` (code and message). Errors found before streaming starts "
                "(404, 422, 503) are returned as normal JSON error responses."
            ),
            "content": {"text/event-stream": {}},
        }
    },
)
def stream_message(
    conversation_id: UUID,
    payload: MessageCreateRequest,
    current_user: CurrentUser,
    service: Service,
    session_factory: Annotated[sessionmaker[Session], Depends(get_session_factory)],
) -> StreamingResponse:
    """Ask a question and receive the answer token by token."""
    turn = service.prepare_turn(
        user_id=current_user.id,
        conversation_id=conversation_id,
        content=payload.content,
        top_k=payload.top_k,
        document_ids=payload.document_ids,
    )
    # Don't hold this request's connection for the length of the stream.
    service.release_connection()

    def events() -> Iterator[str]:
        for event, data in stream_answer(turn, llm=service.llm, session_factory=session_factory):
            if event == "done":
                data = ExchangeResponse(
                    user_message=MessageResponse.from_model(data["user_message"]),
                    assistant_message=MessageResponse.from_model(data["assistant_message"]),
                )
            yield _sse(event, data)

    return StreamingResponse(
        events(),
        media_type="text/event-stream",
        # Stop proxies (e.g. nginx) from buffering the stream.
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )
