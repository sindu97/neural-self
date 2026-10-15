import pytest

from neuralshelf.features.documents.chunking import chunk_pages, split_text


def test_split_text_returns_single_piece_for_short_text() -> None:
    assert split_text("short text", chunk_size=100, overlap=10) == ["short text"]


def test_split_text_returns_nothing_for_empty_text() -> None:
    assert split_text("", chunk_size=100, overlap=10) == []


def test_split_text_respects_size_and_breaks_on_words() -> None:
    words = [f"word{i}" for i in range(500)]
    pieces = split_text(" ".join(words), chunk_size=120, overlap=30)

    assert len(pieces) > 1
    assert all(len(piece) <= 120 for piece in pieces)
    for piece in pieces:
        assert all(token in words for token in piece.split())


def test_split_text_overlaps_consecutive_pieces() -> None:
    text = " ".join(f"w{i}" for i in range(300))
    pieces = split_text(text, chunk_size=100, overlap=30)

    for first, second in zip(pieces, pieces[1:], strict=False):
        assert first.split()[-1] in second.split()


def test_split_text_covers_every_word() -> None:
    words = [f"w{i}" for i in range(400)]
    pieces = split_text(" ".join(words), chunk_size=90, overlap=20)

    seen = {token for piece in pieces for token in piece.split()}
    assert seen == set(words)


def test_split_text_handles_text_without_spaces() -> None:
    pieces = split_text("x" * 250, chunk_size=100, overlap=10)

    assert "".join(pieces).count("x") >= 250
    assert all(len(piece) <= 100 for piece in pieces)


def test_split_text_rejects_overlap_not_smaller_than_size() -> None:
    with pytest.raises(ValueError):
        split_text("abc", chunk_size=10, overlap=10)


def test_chunk_pages_numbers_chunks_and_keeps_pages() -> None:
    chunks = chunk_pages(
        [(1, "alpha  beta\n gamma"), (2, ""), (3, "delta")],
        chunk_size=100,
        overlap=10,
    )

    assert [(c.chunk_index, c.page_number, c.content) for c in chunks] == [
        (0, 1, "alpha beta gamma"),
        (1, 3, "delta"),
    ]
