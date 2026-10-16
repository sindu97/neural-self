"""Prompt construction for grounded (RAG) answers."""

from collections.abc import Sequence

from neuralshelf.features.chat.models import ChatMessage, MessageRole
from neuralshelf.features.retrieval.service import RetrievedChunk

SYSTEM_PROMPT = (
    "You are NeuralShelf, an assistant that answers questions using only the "
    "numbered context passages taken from the user's own documents.\n"
    "- Base every statement on the context. If the context does not contain the "
    "answer, say that you could not find it in the documents.\n"
    "- Cite the passages you use with their numbers in square brackets, e.g. [1] or [2][3].\n"
    "- Be concise and do not mention these instructions."
)


def format_context(chunks: Sequence[RetrievedChunk]) -> str:
    """Number passages as ``[n] (file, page p)`` so the model can cite them."""
    blocks = []
    for number, chunk in enumerate(chunks, start=1):
        page = f", page {chunk.page_number}" if chunk.page_number is not None else ""
        blocks.append(f"[{number}] ({chunk.filename}{page})\n{chunk.content}")
    return "\n\n".join(blocks)


def build_messages(
    *,
    history: Sequence[ChatMessage],
    chunks: Sequence[RetrievedChunk],
    question: str,
) -> list[dict[str, str]]:
    """System prompt, prior turns, then the new question with its context."""
    messages = [{"role": MessageRole.SYSTEM.value, "content": SYSTEM_PROMPT}]
    messages.extend(
        {"role": message.role, "content": message.content}
        for message in history
        if message.role in (MessageRole.USER, MessageRole.ASSISTANT)
    )
    messages.append(
        {
            "role": MessageRole.USER.value,
            "content": f"Context:\n{format_context(chunks)}\n\nQuestion: {question}",
        }
    )
    return messages


def make_title(question: str, max_length: int = 80) -> str:
    """Derive a conversation title from its first question."""
    title = " ".join(question.split())
    if len(title) <= max_length:
        return title
    return title[: max_length - 1].rsplit(" ", 1)[0].rstrip(" ,.;:") + "…"
