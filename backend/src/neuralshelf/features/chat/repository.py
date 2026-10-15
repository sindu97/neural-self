"""Database operations for conversations and messages."""

from collections.abc import Sequence
from datetime import datetime
from typing import Any
from uuid import UUID

from sqlalchemy import delete, func, select
from sqlalchemy.orm import Session

from neuralshelf.features.chat.models import ChatMessage, Conversation


class ConversationRepository:
    """Every conversation read and delete is scoped by ``user_id``."""

    def __init__(self, db: Session) -> None:
        self.db = db

    def create(self, *, user_id: UUID, title: str | None) -> Conversation:
        conversation = Conversation(user_id=user_id, title=title)
        self.db.add(conversation)
        self.db.flush()
        return conversation

    def get_owned(self, *, user_id: UUID, conversation_id: UUID) -> Conversation | None:
        statement = select(Conversation).where(
            Conversation.id == conversation_id,
            Conversation.user_id == user_id,
        )
        return self.db.scalar(statement)

    def list_owned(
        self, *, user_id: UUID, limit: int, offset: int
    ) -> tuple[Sequence[Conversation], int]:
        statement = (
            select(Conversation)
            .where(Conversation.user_id == user_id)
            .order_by(Conversation.updated_at.desc(), Conversation.id)
            .limit(limit)
            .offset(offset)
        )
        total = self.db.scalar(
            select(func.count()).select_from(Conversation).where(Conversation.user_id == user_id)
        )
        return self.db.scalars(statement).all(), total or 0

    def delete(self, conversation: Conversation) -> None:
        # messages are removed by the ON DELETE CASCADE foreign key.
        self.db.execute(delete(Conversation).where(Conversation.id == conversation.id))

    def list_messages(
        self, *, conversation_id: UUID, limit: int, offset: int
    ) -> tuple[Sequence[ChatMessage], int]:
        """Messages in chronological order."""
        statement = (
            select(ChatMessage)
            .where(ChatMessage.conversation_id == conversation_id)
            .order_by(ChatMessage.created_at, ChatMessage.id)
            .limit(limit)
            .offset(offset)
        )
        total = self.db.scalar(
            select(func.count())
            .select_from(ChatMessage)
            .where(ChatMessage.conversation_id == conversation_id)
        )
        return self.db.scalars(statement).all(), total or 0

    def recent_messages(self, *, conversation_id: UUID, limit: int) -> list[ChatMessage]:
        """The latest ``limit`` messages, returned oldest first."""
        if limit <= 0:
            return []
        statement = (
            select(ChatMessage)
            .where(ChatMessage.conversation_id == conversation_id)
            .order_by(ChatMessage.created_at.desc(), ChatMessage.id)
            .limit(limit)
        )
        return list(reversed(self.db.scalars(statement).all()))

    def add_message(
        self,
        *,
        conversation_id: UUID,
        role: str,
        content: str,
        created_at: datetime,
        metadata: dict[str, Any] | None = None,
    ) -> ChatMessage:
        message = ChatMessage(
            conversation_id=conversation_id,
            role=role,
            content=content,
            created_at=created_at,
            message_metadata=metadata,
        )
        self.db.add(message)
        self.db.flush()
        return message
