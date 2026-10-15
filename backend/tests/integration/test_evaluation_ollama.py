"""Quality checks against the real Ollama models.

Excluded from the default run (slow, needs Ollama). Run with:
    pytest -m evaluation
"""

import httpx
import pytest

from neuralshelf.core.config import get_settings
from neuralshelf.core.constants import EMBEDDING_DIMENSIONS
from neuralshelf.integrations.dependencies import get_chat_client, get_embedding_client
from neuralshelf.main import app
from tests.pdf_factory import make_pdf

pytestmark = [pytest.mark.evaluation, pytest.mark.integration]

API = "/api/v1"

CORPUS = {
    "biology.pdf": [
        "Photosynthesis takes place in the chloroplasts of plant cells. Chlorophyll absorbs "
        "sunlight, and the plant turns water and carbon dioxide into glucose and oxygen.",
        "Mitochondria are the powerhouse of the cell, producing ATP through cellular respiration.",
    ],
    "history.pdf": [
        "The French Revolution began in 1789 with the storming of the Bastille in Paris.",
        "The Roman aqueducts carried fresh water into cities using gravity and stone arches.",
    ],
    "geology.pdf": [
        "Volcanoes erupt when magma from the Earth's mantle rises through cracks in the crust.",
    ],
}

# question -> (expected file, expected page)
RETRIEVAL_CASES = {
    "Where in the cell does photosynthesis happen?": ("biology.pdf", 1),
    "Which organelle produces ATP energy?": ("biology.pdf", 2),
    "When did the French Revolution start?": ("history.pdf", 1),
    "How did Romans bring water to their cities?": ("history.pdf", 2),
    "What causes a volcanic eruption?": ("geology.pdf", 1),
}


@pytest.fixture(scope="module", autouse=True)
def require_ollama() -> None:
    try:
        httpx.get(f"{get_settings().ollama_base_url}/api/tags", timeout=3).raise_for_status()
    except httpx.HTTPError:
        pytest.skip("Ollama is not reachable.")


@pytest.fixture
def real_client(client):
    """The test client, but with the real Ollama embedding and chat clients."""
    app.dependency_overrides.pop(get_embedding_client)
    app.dependency_overrides.pop(get_chat_client)
    return client


@pytest.fixture
def library(real_client, auth_headers, make_worker):
    headers = auth_headers("eval@example.com")
    for filename, pages in CORPUS.items():
        response = real_client.post(
            f"{API}/documents",
            headers=headers,
            files={"file": (filename, make_pdf(pages), "application/pdf")},
        )
        assert response.status_code == 202
    make_worker(embedder_override=get_embedding_client()).run_until_idle()

    documents = real_client.get(f"{API}/documents", headers=headers).json()["data"]
    assert {d["status"] for d in documents} == {"completed"}
    return headers


def test_embedding_model_matches_vector_column() -> None:
    vector = get_embedding_client().embed_query("dimension check")
    assert len(vector) == EMBEDDING_DIMENSIONS


def test_retrieval_ranks_the_right_page_first(real_client, library) -> None:
    hits = 0
    for question, (filename, page) in RETRIEVAL_CASES.items():
        results = real_client.post(
            f"{API}/retrieval/search", headers=library, json={"query": question, "top_k": 3}
        ).json()["data"]
        top = results[0]
        hits += (top["filename"], top["page_number"]) == (filename, page)

    # Top-1 accuracy; tolerate one miss so a model update doesn't flake the suite.
    assert hits >= len(RETRIEVAL_CASES) - 1, f"top-1 hits: {hits}/{len(RETRIEVAL_CASES)}"


def test_grounded_answer_cites_the_source(real_client, library) -> None:
    conversation = real_client.post(f"{API}/conversations", headers=library).json()["data"][0]

    response = real_client.post(
        f"{API}/conversations/{conversation['id']}/messages",
        headers=library,
        json={"content": "Where does photosynthesis take place?", "top_k": 2},
    )

    assert response.status_code == 201, response.text
    answer = response.json()["data"][0]["assistant_message"]
    assert "chloroplast" in answer["content"].lower()
    assert answer["citations"][0]["filename"] == "biology.pdf"


def test_streamed_answer_arrives_in_several_fragments(real_client, library) -> None:
    conversation = real_client.post(f"{API}/conversations", headers=library).json()["data"][0]

    response = real_client.post(
        f"{API}/conversations/{conversation['id']}/messages/stream",
        headers=library,
        json={"content": "When did the French Revolution begin?", "top_k": 2},
    )

    tokens = [line for line in response.text.splitlines() if line == "event: token"]
    assert len(tokens) > 1
    assert "event: done" in response.text
    assert "1789" in response.text
