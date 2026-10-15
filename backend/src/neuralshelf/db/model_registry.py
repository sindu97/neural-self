"""Import every feature's models so they register on Base.metadata.

This is the one module in db/ allowed to import from features/. Import it only
from migrations/env.py and main.py, never from db/base.py or a feature module,
to avoid circular imports.
"""

from neuralshelf.features.auth.models import RateLimitBucket, RefreshToken
from neuralshelf.features.chat.models import ChatMessage, Conversation
from neuralshelf.features.documents.models import Chunk, Document, IngestionJob
from neuralshelf.features.users.models import User

__all__ = [
    "ChatMessage",
    "Chunk",
    "Conversation",
    "Document",
    "IngestionJob",
    "RateLimitBucket",
    "RefreshToken",
    "User",
]
