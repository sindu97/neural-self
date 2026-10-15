"""The HNSW index is used, and filtered vector search still returns full results.

How Postgres plans "nearest chunks owned by this user":
- If the filter is selective (a user with few documents), the planner uses the
  btree indexes to fetch that user's chunks and sorts them exactly. Perfect
  recall; no HNSW involved.
- If it uses HNSW, the index returns the nearest ~40 candidates
  (hnsw.ef_search) across *all* rows and the filter runs afterwards. When
  other users' chunks crowd those candidates, too few rows survive. The
  iterative scan (pgvector >= 0.8) keeps walking the index until LIMIT is met.

The tests force the HNSW path with a filter that has no index (page_number).
"""

import random
import uuid

import pytest
from sqlalchemy import insert, text

from neuralshelf.core.constants import EMBEDDING_DIMENSIONS
from neuralshelf.features.documents.models import Chunk, Document, DocumentStatus
from neuralshelf.features.retrieval.repository import RetrievalRepository
from neuralshelf.features.users.models import User

pytestmark = pytest.mark.integration


def random_vector(rng: random.Random, near: list[float] | None = None, spread: float = 1.0):
    """Gaussian vector; with ``near``, a noisy copy of it (so it's close to ``near``)."""
    noise = [rng.gauss(0, spread) for _ in range(EMBEDDING_DIMENSIONS)]
    if near is None:
        return noise
    return [base + n for base, n in zip(near, noise, strict=True)]


def create_user_with_chunks(
    db, email: str, embeddings: list[list[float]], page_number: int
) -> uuid.UUID:
    user = User(name="Vector", email=email, password_hash="x")
    db.add(user)
    db.flush()
    document = Document(
        user_id=user.id, filename=f"{email}.pdf", status=DocumentStatus.COMPLETED
    )
    db.add(document)
    db.flush()
    db.execute(
        insert(Chunk),
        [
            {
                "document_id": document.id,
                "chunk_index": index,
                "page_number": page_number,
                "content": f"chunk {index}",
                "embedding": embedding,
            }
            for index, embedding in enumerate(embeddings)
        ],
    )
    return user.id


RNG_SEED = 1234
QUERY = random_vector(random.Random(RNG_SEED))


@pytest.fixture
def crowded_index(session_factory):
    """User A: 5 unrelated chunks (page 2). User B: 300 chunks close to QUERY (page 1)."""
    rng = random.Random(RNG_SEED + 1)
    with session_factory() as db:
        user_a = create_user_with_chunks(
            db, "a@example.com", [random_vector(rng) for _ in range(5)], 2
        )
        create_user_with_chunks(
            db, "b@example.com", [random_vector(rng, QUERY, 0.3) for _ in range(300)], 1
        )
        db.commit()
    return user_a


def exact_order(db, user_id) -> list[int]:
    """Ground truth: the user's chunks by exact distance (sequential scan, no index)."""
    db.execute(text("SET LOCAL enable_indexscan = off"))
    db.execute(text("SET LOCAL enable_bitmapscan = off"))
    return list(
        db.execute(
            text(
                "SELECT c.chunk_index FROM chunks c JOIN documents d ON d.id = c.document_id "
                "WHERE d.user_id = :user_id ORDER BY c.embedding <=> :q"
            ),
            {"user_id": user_id, "q": str(QUERY)},
        ).scalars()
    )


def test_hnsw_index_exists_and_is_valid(session_factory) -> None:
    with session_factory() as db:
        valid = db.scalar(
            text(
                "SELECT i.indisvalid FROM pg_index i JOIN pg_class c ON c.oid = i.indexrelid "
                "WHERE c.relname = 'ix_chunks_embedding_hnsw'"
            )
        )
    assert valid is True


def test_similarity_query_uses_the_hnsw_index(session_factory, crowded_index) -> None:
    with session_factory() as db:
        # Tiny test tables would normally be scanned sequentially; disable that
        # to confirm the planner can use the index for our ORDER BY <=>.
        db.execute(text("SET LOCAL enable_seqscan = off"))
        plan = "\n".join(
            db.execute(
                text("EXPLAIN SELECT id FROM chunks ORDER BY embedding <=> :q LIMIT 5"),
                {"q": str(QUERY)},
            ).scalars()
        )
    assert "ix_chunks_embedding_hnsw" in plan


FILTERED_QUERY = text(
    "SELECT id FROM chunks WHERE page_number = 2 ORDER BY embedding <=> :q LIMIT 5"
)


def filtered_search(db, iterative_scan: str) -> list:
    db.execute(text("SET LOCAL enable_seqscan = off"))
    db.execute(text(f"SET LOCAL hnsw.iterative_scan = {iterative_scan}"))
    plan = "\n".join(
        db.execute(text(f"EXPLAIN {FILTERED_QUERY.text}"), {"q": str(QUERY)}).scalars()
    )
    assert "ix_chunks_embedding_hnsw" in plan
    return db.execute(FILTERED_QUERY, {"q": str(QUERY)}).all()


def test_plain_hnsw_scan_loses_results_when_filtering(session_factory, crowded_index) -> None:
    with session_factory() as db:
        rows = filtered_search(db, "off")
    assert len(rows) < 5  # the problem the iterative scan solves


def test_iterative_hnsw_scan_returns_full_results_when_filtering(
    session_factory, crowded_index
) -> None:
    with session_factory() as db:
        rows = filtered_search(db, "strict_order")
    assert len(rows) == 5


def test_retrieval_returns_full_ordered_results_for_the_user(
    session_factory, crowded_index
) -> None:
    with session_factory() as db:
        rows = RetrievalRepository(db).nearest_chunks(
            user_id=crowded_index, query_embedding=QUERY, top_k=5
        )
    with session_factory() as db:
        expected = exact_order(db, crowded_index)

    assert [row.chunk_index for row in rows] == expected
    distances = [row.distance for row in rows]
    assert distances == sorted(distances)
