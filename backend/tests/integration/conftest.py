"""Fixtures for API tests against a real PostgreSQL + pgvector database.

Tests use a separate ``neuralshelf_test`` database on the same server as
DATABASE_URL, so development data is never touched. Ollama is replaced
with deterministic fakes.
"""

import hashlib
import math
import re
from collections.abc import Callable, Generator

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import Engine, create_engine, make_url, text
from sqlalchemy.exc import OperationalError
from sqlalchemy.orm import Session, sessionmaker

from neuralshelf.core.config import get_settings
from neuralshelf.core.constants import EMBEDDING_DIMENSIONS
from neuralshelf.db.base import Base
from neuralshelf.db.session import get_db, get_session_factory
from neuralshelf.features.documents.ingestion import JobContext
from neuralshelf.features.documents.storage import LocalFileStorage, get_file_storage
from neuralshelf.integrations.dependencies import get_chat_client, get_embedding_client
from neuralshelf.main import app
from neuralshelf.workers.ingestion_worker import IngestionWorker

TEST_DATABASE_NAME = "neuralshelf_test"


class FakeEmbedder:
    """Bag-of-words hashing embedder: texts sharing words are similar."""

    def _embed(self, text_value: str) -> list[float]:
        vector = [0.0] * EMBEDDING_DIMENSIONS
        for word in re.findall(r"\w+", text_value.lower()):
            vector[int(hashlib.md5(word.encode()).hexdigest(), 16) % EMBEDDING_DIMENSIONS] += 1
        norm = math.sqrt(sum(v * v for v in vector)) or 1.0
        if not any(vector):
            vector[0] = 1.0
        return [v / norm for v in vector]

    def embed_documents(self, texts: list[str]) -> list[list[float]]:
        return [self._embed(t) for t in texts]

    def embed_query(self, text_value: str) -> list[float]:
        return self._embed(text_value)


class FakeChatClient:
    model = "fake-chat-model"

    def __init__(self) -> None:
        self.calls: list[list[dict[str, str]]] = []

    answer = "According to the documents, plants convert light into energy [1]."

    def chat(self, messages: list[dict[str, str]]) -> str:
        self.calls.append(messages)
        return self.answer

    def stream_chat(self, messages: list[dict[str, str]]):
        self.calls.append(messages)
        words = self.answer.split(" ")
        for index, word in enumerate(words):
            yield word if index == len(words) - 1 else f"{word} "


@pytest.fixture(scope="session")
def engine() -> Generator[Engine, None, None]:
    url = make_url(get_settings().database_url.get_secret_value()).set(
        drivername="postgresql+psycopg"
    )
    admin_engine = create_engine(url, isolation_level="AUTOCOMMIT")
    try:
        with admin_engine.connect() as connection:
            exists = connection.execute(
                text("SELECT 1 FROM pg_database WHERE datname = :name"),
                {"name": TEST_DATABASE_NAME},
            ).scalar()
            if not exists:
                connection.execute(text(f'CREATE DATABASE "{TEST_DATABASE_NAME}"'))
    except OperationalError:
        pytest.skip("PostgreSQL is not reachable; start it with `docker compose up -d db`.")
    finally:
        admin_engine.dispose()

    test_engine = create_engine(url.set(database=TEST_DATABASE_NAME))
    with test_engine.begin() as connection:
        connection.execute(text("CREATE EXTENSION IF NOT EXISTS vector"))
    Base.metadata.drop_all(test_engine)
    Base.metadata.create_all(test_engine)

    yield test_engine

    test_engine.dispose()


@pytest.fixture
def session_factory(engine: Engine) -> sessionmaker[Session]:
    table_names = ", ".join(table.name for table in Base.metadata.sorted_tables)
    with engine.begin() as connection:
        connection.execute(text(f"TRUNCATE {table_names} CASCADE"))
    return sessionmaker(bind=engine, autoflush=False, expire_on_commit=False)


@pytest.fixture
def chat_client() -> FakeChatClient:
    return FakeChatClient()


@pytest.fixture
def storage(tmp_path) -> LocalFileStorage:
    return LocalFileStorage(tmp_path / "uploads")


@pytest.fixture
def embedder() -> FakeEmbedder:
    return FakeEmbedder()


@pytest.fixture
def make_worker(
    session_factory: sessionmaker[Session],
    storage: LocalFileStorage,
    embedder: FakeEmbedder,
) -> Callable[..., IngestionWorker]:
    """Build an in-process worker; tests call run_once()/run_until_idle()."""

    def _make_worker(worker_id: str = "test-worker", embedder_override=None) -> IngestionWorker:
        return IngestionWorker(
            JobContext(
                session_factory=session_factory,
                storage=storage,
                embedder=embedder_override or embedder,
                worker_id=worker_id,
            )
        )

    return _make_worker


@pytest.fixture
def worker(make_worker: Callable[..., IngestionWorker]) -> IngestionWorker:
    return make_worker()


@pytest.fixture
def client(
    session_factory: sessionmaker[Session],
    chat_client: FakeChatClient,
    storage: LocalFileStorage,
    embedder: FakeEmbedder,
) -> Generator[TestClient, None, None]:
    def override_get_db() -> Generator[Session, None, None]:
        with session_factory() as session:
            yield session

    app.dependency_overrides.update(
        {
            get_db: override_get_db,
            get_session_factory: lambda: session_factory,
            get_embedding_client: lambda: embedder,
            get_chat_client: lambda: chat_client,
            get_file_storage: lambda: storage,
        }
    )
    yield TestClient(app)
    app.dependency_overrides.clear()


@pytest.fixture
def auth_headers(client: TestClient) -> Callable[[str], dict[str, str]]:
    """Sign up and log in a user; returns their Authorization header."""

    def _auth_headers(email: str) -> dict[str, str]:
        password = "CorrectHorse!42"
        response = client.post(
            "/api/v1/auth/signup",
            json={"name": "Test User", "email": email, "password": password},
        )
        assert response.status_code == 201, response.text
        response = client.post(
            "/api/v1/auth/login", json={"email": email, "password": password}
        )
        assert response.status_code == 200, response.text
        token = response.json()["data"][0]["access_token"]
        return {"Authorization": f"Bearer {token}"}

    return _auth_headers

