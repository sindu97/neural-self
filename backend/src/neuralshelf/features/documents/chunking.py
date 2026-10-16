"""Split extracted page text into overlapping chunks."""

from collections.abc import Iterable
from dataclasses import dataclass


@dataclass(frozen=True)
class TextChunk:
    """A piece of one page's text, with its position in the document."""

    chunk_index: int
    page_number: int | None
    content: str


def split_text(text: str, *, chunk_size: int, overlap: int) -> list[str]:
    """Split text into pieces of at most ``chunk_size`` characters.

    Pieces break on whitespace where possible and consecutive pieces share
    roughly ``overlap`` characters, so a sentence cut at a boundary still
    appears whole in one of them.
    """
    if overlap >= chunk_size:
        raise ValueError("overlap must be smaller than chunk_size")

    pieces: list[str] = []
    start = 0
    length = len(text)

    while start < length:
        end = min(start + chunk_size, length)
        if end < length:
            # Break at the last space, but past the overlap so we always advance.
            space = text.rfind(" ", start + overlap + 1, end)
            if space != -1:
                end = space

        piece = text[start:end].strip()
        if piece:
            pieces.append(piece)
        if end >= length:
            break

        next_start = end - overlap
        space = text.find(" ", next_start, end)
        start = space + 1 if space != -1 else next_start

    return pieces


def chunk_pages(
    pages: Iterable[tuple[int, str]],
    *,
    chunk_size: int,
    overlap: int,
) -> list[TextChunk]:
    """Chunk each page separately so every chunk maps to a single page."""
    chunks: list[TextChunk] = []
    for page_number, text in pages:
        normalized = " ".join(text.split())
        for piece in split_text(normalized, chunk_size=chunk_size, overlap=overlap):
            chunks.append(TextChunk(len(chunks), page_number, piece))
    return chunks
