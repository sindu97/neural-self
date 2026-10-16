"""Business logic for persistent, document-grounded conversations."""

import logging
from collections.abc import Iterable, Iterator, Sequence
from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Any
from uuid import UUID

from sqlalchemy.orm import Session, sessionmaker

from neuralshelf.core.config import get_settings
from neuralshelf.core.exceptions import ApplicationError
from neuralshelf.core.messages import Message, MessageCode
from neuralshelf.features.chat.models import ChatMessage, Conversation, MessageRole
from neuralshelf.features.chat.prompts import build_messages, make_title
from neuralshelf.features.chat.repository import ConversationRepository
from neuralshelf.features.retrieval.service import RetrievalService, RetrievedChunk
from neuralshelf.integrations.llm.ollama import ChatClient

logger = logging.getLogger(__name__)

EXCERPT_LENGTH = 300

StreamEvent = tuple[str, dict[str, Any]]


@dataclass(frozen=True)
class PreparedTurn:
    """Everything needed to answer one question, gathered before generation."""

    conversation_id: UUID
    question: str
    received_at: datetime
    prompt: list[dict[str, str]] | None  # None: no relevant context was found
    metadata: dict[str, Any]


class ConversationNotFoundError(ApplicationError):
    """Raised for missing conversations and those owned by another user alike."""

    def __init__(self) -> None:
        super().__init__(
            message=Message.CONVERSATION_NOT_FOUND,
            code=MessageCode.CONVERSATION_NOT_FOUND,
            status_code=404,
        )


def _citations(chunks: Sequence[RetrievedChunk]) -> list[dict[str, Any]]:
    return [
        {
            "number": number,
            "document_id": str(chunk.document_id),
            "filename": chunk.filename,
            "page_number": chunk.page_number,
            "chunk_index": chunk.chunk_index,
            "score": chunk.score,
            "excerpt": chunk.content[:EXCERPT_LENGTH],
        }
        for number, chunk in enumerate(chunks, start=1)
    ]


class ChatService:
    """Conversations and grounded answers, always scoped to one user."""

    def __init__(self, db: Session, retrieval: RetrievalService, llm: ChatClient) -> None:
        self.db = db
        self.repository = ConversationRepository(db)
        self.retrieval = retrieval
        self.llm = llm

    def create_conversation(self, *, user_id: UUID, title: str | None) -> Conversation:
        """Create and commit an empty conversation."""
        conversation = self.repository.create(user_id=user_id, title=title)
        self.db.commit()
        return conversation

    def list_conversations(
        self, *, user_id: UUID, limit: int, offset: int
    ) -> tuple[Sequence[Conversation], int]:
        """The user's conversations, most recently active first, and their total count."""
        return self.repository.list_owned(user_id=user_id, limit=limit, offset=offset)

    def get_conversation(self, *, user_id: UUID, conversation_id: UUID) -> Conversation:
        """The user's conversation.

        Raises:
            ConversationNotFoundError: Missing, or owned by another user.
        """
        conversation = self.repository.get_owned(user_id=user_id, conversation_id=conversation_id)
        if conversation is None:
            raise ConversationNotFoundError()
        return conversation

    def delete_conversation(self, *, user_id: UUID, conversation_id: UUID) -> None:
        """Delete the user's conversation and all its messages."""
        conversation = self.get_conversation(user_id=user_id, conversation_id=conversation_id)
        self.repository.delete(conversation)
        self.db.commit()

    def list_messages(
        self, *, user_id: UUID, conversation_id: UUID, limit: int, offset: int
    ) -> tuple[Sequence[ChatMessage], int]:
        """A page of the conversation's messages, oldest first, and their total count."""
        conversation = self.get_conversation(user_id=user_id, conversation_id=conversation_id)
        return self.repository.list_messages(
            conversation_id=conversation.id, limit=limit, offset=offset
        )

    def prepare_turn(
        self,
        *,
        user_id: UUID,
        conversation_id: UUID,
        content: str,
        top_k: int,
        document_ids: Sequence[UUID] = (),
    ) -> PreparedTurn:
        """Check ownership, retrieve context and build the prompt.

        Everything that can fail with a normal error response happens here,
        before any answer is generated or streamed.
        """
        received_at = datetime.now(UTC)
        conversation = self.get_conversation(user_id=user_id, conversation_id=conversation_id)

        history = self.repository.recent_messages(
            conversation_id=conversation.id,
            limit=get_settings().chat_history_max_messages,
        )
        chunks = self.retrieval.search(
            user_id=user_id, query=content, top_k=top_k, document_ids=document_ids
        )

        if not chunks:
            # Nothing to ground an answer in; don't let the model guess.
            return PreparedTurn(conversation.id, content, received_at, None, {"citations": []})

        return PreparedTurn(
            conversation_id=conversation.id,
            question=content,
            received_at=received_at,
            prompt=build_messages(history=history, chunks=chunks, question=content),
            metadata={"citations": _citations(chunks), "model": self.llm.model},
        )

    def release_connection(self) -> None:
        """End the (read-only) transaction so the connection returns to the pool."""
        self.db.rollback()

    def send_message(
        self,
        *,
        user_id: UUID,
        conversation_id: UUID,
        content: str,
        top_k: int,
        document_ids: Sequence[UUID] = (),
    ) -> tuple[ChatMessage, ChatMessage]:
        """Answer a question from the user's documents and save both turns.

        Nothing is saved if retrieval or generation fails, so the client can
        safely retry the same question.
        """
        turn = self.prepare_turn(
            user_id=user_id,
            conversation_id=conversation_id,
            content=content,
            top_k=top_k,
            document_ids=document_ids,
        )
        answer = self.llm.chat(turn.prompt) if turn.prompt else Message.NO_RELEVANT_CONTEXT
        return save_turn(self.db, turn, answer)


def stream_answer(
    turn: PreparedTurn,
    *,
    llm: ChatClient,
    session_factory: sessionmaker[Session],
) -> Iterator[StreamEvent]:
    """Yield ``(event, data)`` pairs: start, token..., then done or error.

    No database connection is held while tokens stream (that can take many
    seconds); a fresh session saves the exchange once the answer is complete.
    If the client disconnects mid-stream the generator is closed and nothing
    is saved, so a retried question never leaves a half answer behind.
    """
    yield "start", {
        "conversation_id": str(turn.conversation_id),
        "citations": turn.metadata["citations"],
    }
    try:
        if turn.prompt is None:
            fragments: Iterable[str] = [Message.NO_RELEVANT_CONTEXT]
        else:
            fragments = llm.stream_chat(turn.prompt)

        parts: list[str] = []
        for fragment in fragments:
            parts.append(fragment)
            yield "token", {"delta": fragment}

        with session_factory() as db:
            user_message, assistant_message = save_turn(db, turn, "".join(parts).strip())
        yield "done", {"user_message": user_message, "assistant_message": assistant_message}

    except ApplicationError as exc:
        yield "error", {"code": exc.code, "message": exc.message}
    except Exception:
        logger.exception("Streaming answer failed.")
        yield "error", {
            "code": MessageCode.INTERNAL_SERVER_ERROR,
            "message": Message.INTERNAL_SERVER_ERROR,
        }


def save_turn(
    db: Session, turn: PreparedTurn, answer: str
) -> tuple[ChatMessage, ChatMessage]:
    """Persist the question and its answer, and touch the conversation."""
    repository = ConversationRepository(db)
    conversation = db.get(Conversation, turn.conversation_id)
    if conversation is None:  # deleted while the answer was being generated
        raise ConversationNotFoundError()

    user_message = repository.add_message(
        conversation_id=conversation.id,
        role=MessageRole.USER,
        content=turn.question,
        created_at=turn.received_at,
    )
    answered_at = datetime.now(UTC)
    assistant_message = repository.add_message(
        conversation_id=conversation.id,
        role=MessageRole.ASSISTANT,
        content=answer,
        created_at=answered_at,
        metadata=turn.metadata,
    )

    if conversation.title is None:
        conversation.title = make_title(turn.question)
    conversation.updated_at = answered_at
    db.commit()

    return user_message, assistant_message
