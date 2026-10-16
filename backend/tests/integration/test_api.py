"""End-to-end API tests: documents, retrieval, chat, auth and user isolation."""

from typing import Any

import pytest
from sqlalchemy import func, select

from neuralshelf.core.messages import Message
from neuralshelf.db.seeders.sample_pdf import make_pdf
from neuralshelf.features.auth.models import RefreshToken
from neuralshelf.features.documents.models import Chunk

pytestmark = pytest.mark.integration

API = "/api/v1"
PHOTOSYNTHESIS = "Photosynthesis lets plants convert sunlight water and carbon dioxide into sugar."
RAILWAYS = "The railway network expanded quickly during the industrial revolution in Britain."


def item(response: Any) -> Any:
    """Return the single item in a success envelope."""
    body = response.json()
    assert body["success"] is True, body
    return body["data"][0]


def upload(client, headers, pages: list[str], filename: str = "notes.pdf") -> dict:
    response = client.post(
        f"{API}/documents",
        headers=headers,
        files={"file": (filename, make_pdf(pages), "application/pdf")},
    )
    assert response.status_code == 202, response.text
    return item(response)


@pytest.fixture
def upload_and_ingest(client, worker):
    """Upload, then let the worker drain the queue, like the worker service would."""

    def _upload_and_ingest(headers, pages: list[str], filename: str = "notes.pdf") -> dict:
        document = upload(client, headers, pages, filename)
        worker.run_until_idle()
        return document

    return _upload_and_ingest


def chunk_count(session_factory, document_id: str) -> int:
    with session_factory() as db:
        return db.scalar(
            select(func.count()).select_from(Chunk).where(Chunk.document_id == document_id)
        )


def test_protected_endpoints_require_authentication(client) -> None:
    for method, path in [
        ("get", "/documents"),
        ("post", "/retrieval/search"),
        ("get", "/conversations"),
    ]:
        response = getattr(client, method)(f"{API}{path}")
        assert response.status_code == 401
        assert response.json()["success"] is False


def test_document_upload_ingest_list_get_and_delete(
    client, auth_headers, session_factory, storage, upload_and_ingest
) -> None:
    headers = auth_headers("alice@example.com")

    document = upload_and_ingest(headers, [PHOTOSYNTHESIS, RAILWAYS])
    assert document["status"] == "uploaded"
    assert document["filename"] == "notes.pdf"

    response = client.get(f"{API}/documents/{document['id']}", headers=headers)
    assert response.status_code == 200
    assert item(response)["status"] == "completed"
    assert chunk_count(session_factory, document["id"]) == 2

    listing = client.get(f"{API}/documents", headers=headers).json()
    assert listing["pagination"] == {"limit": 20, "offset": 0, "total": 1}
    assert [d["id"] for d in listing["data"]] == [document["id"]]

    stored_files = list(storage.root.rglob("*.pdf"))
    assert len(stored_files) == 1

    response = client.delete(f"{API}/documents/{document['id']}", headers=headers)
    assert response.status_code == 200
    assert chunk_count(session_factory, document["id"]) == 0
    assert not stored_files[0].exists()
    assert client.get(f"{API}/documents/{document['id']}", headers=headers).status_code == 404


def test_upload_rejects_files_that_are_not_pdfs(client, auth_headers) -> None:
    headers = auth_headers("alice@example.com")

    for filename, content, content_type in [
        ("notes.txt", b"plain text", "text/plain"),
        ("renamed.pdf", b"plain text pretending to be a pdf", "application/pdf"),
    ]:
        response = client.post(
            f"{API}/documents",
            headers=headers,
            files={"file": (filename, content, content_type)},
        )
        assert response.status_code == 422
        assert response.json()["code"] == "INVALID_FILE"


def test_pdf_without_text_fails_and_can_be_reprocessed(
    client, auth_headers, worker, upload_and_ingest
) -> None:
    headers = auth_headers("alice@example.com")
    document = upload_and_ingest(headers, [""])

    failed = item(client.get(f"{API}/documents/{document['id']}", headers=headers))
    assert failed["status"] == "failed"
    assert failed["error_message"] == Message.INGESTION_NO_TEXT

    response = client.post(f"{API}/documents/{document['id']}/reprocess", headers=headers)
    assert response.status_code == 202
    assert item(response)["status"] == "uploaded"
    worker.run_until_idle()
    again = item(client.get(f"{API}/documents/{document['id']}", headers=headers))
    assert again["status"] == "failed"


def test_search_ranks_relevant_chunks_with_source_metadata(
    client, auth_headers, upload_and_ingest
) -> None:
    headers = auth_headers("alice@example.com")
    document = upload_and_ingest(headers, [RAILWAYS, PHOTOSYNTHESIS], filename="biology.pdf")

    response = client.post(
        f"{API}/retrieval/search",
        headers=headers,
        json={"query": "How do plants use sunlight?", "top_k": 2},
    )
    assert response.status_code == 200
    results = response.json()["data"]
    assert len(results) == 2
    assert results[0]["page_number"] == 2
    assert results[0]["document_id"] == document["id"]
    assert results[0]["filename"] == "biology.pdf"
    assert results[0]["score"] > results[1]["score"]


def test_search_validates_bounds(client, auth_headers) -> None:
    headers = auth_headers("alice@example.com")

    for payload in [{"query": "x", "top_k": 0}, {"query": "x", "top_k": 1000}, {"query": "  "}]:
        response = client.post(f"{API}/retrieval/search", headers=headers, json=payload)
        assert response.status_code == 422
    assert client.get(f"{API}/documents?limit=1000", headers=headers).status_code == 422


def test_users_cannot_access_each_others_data(client, auth_headers, upload_and_ingest) -> None:
    alice = auth_headers("alice@example.com")
    bob = auth_headers("bob@example.com")

    document = upload_and_ingest(alice, [PHOTOSYNTHESIS])
    conversation = item(client.post(f"{API}/conversations", headers=alice, json={}))
    doc_url = f"{API}/documents/{document['id']}"
    conv_url = f"{API}/conversations/{conversation['id']}"

    assert client.get(doc_url, headers=bob).status_code == 404
    assert client.delete(doc_url, headers=bob).status_code == 404
    assert client.post(f"{doc_url}/reprocess", headers=bob).status_code == 404
    assert client.get(f"{API}/documents", headers=bob).json()["data"] == []

    search = client.post(
        f"{API}/retrieval/search",
        headers=bob,
        json={"query": "plants sunlight", "document_ids": [document["id"]]},
    )
    assert search.status_code == 404
    search = client.post(f"{API}/retrieval/search", headers=bob, json={"query": "plants"})
    assert search.json()["data"] == []

    assert client.get(conv_url, headers=bob).status_code == 404
    assert client.get(f"{conv_url}/messages", headers=bob).status_code == 404
    assert (
        client.post(f"{conv_url}/messages", headers=bob, json={"content": "hi"}).status_code
        == 404
    )
    assert client.delete(conv_url, headers=bob).status_code == 404
    assert client.get(f"{API}/conversations", headers=bob).json()["data"] == []

    # Alice still has everything.
    assert client.get(doc_url, headers=alice).status_code == 200
    assert client.get(conv_url, headers=alice).status_code == 200


def test_conversation_answers_with_citations_and_history(
    client, auth_headers, chat_client, upload_and_ingest
) -> None:
    headers = auth_headers("alice@example.com")
    document = upload_and_ingest(headers, [PHOTOSYNTHESIS], filename="biology.pdf")
    conversation = item(client.post(f"{API}/conversations", headers=headers))
    assert conversation["title"] is None
    messages_url = f"{API}/conversations/{conversation['id']}/messages"

    response = client.post(
        messages_url, headers=headers, json={"content": "What does photosynthesis do?"}
    )
    assert response.status_code == 201, response.text
    exchange = item(response)
    assert exchange["user_message"]["role"] == "user"
    answer = exchange["assistant_message"]
    assert answer["role"] == "assistant"
    assert answer["content"] == "According to the documents, plants convert light into energy [1]."
    assert answer["citations"][0]["number"] == 1
    assert answer["citations"][0]["document_id"] == document["id"]
    assert answer["citations"][0]["filename"] == "biology.pdf"
    assert answer["citations"][0]["page_number"] == 1

    prompt = chat_client.calls[0]
    assert prompt[0]["role"] == "system"
    assert "Photosynthesis lets plants" in prompt[-1]["content"]

    client.post(messages_url, headers=headers, json={"content": "And what about sugar?"})
    # The second prompt includes the first question and answer as history.
    second_prompt = chat_client.calls[1]
    assert [m["role"] for m in second_prompt] == ["system", "user", "assistant", "user"]

    history = client.get(messages_url, headers=headers).json()
    assert history["pagination"]["total"] == 4
    assert [m["role"] for m in history["data"]] == ["user", "assistant", "user", "assistant"]
    assert history["data"][1]["citations"]

    titled = item(client.get(f"{API}/conversations/{conversation['id']}", headers=headers))
    assert titled["title"] == "What does photosynthesis do?"

    conversation_url = f"{API}/conversations/{conversation['id']}"
    assert client.delete(conversation_url, headers=headers).status_code == 200
    assert client.get(messages_url, headers=headers).status_code == 404


def test_question_without_documents_does_not_call_the_model(
    client, auth_headers, chat_client
) -> None:
    headers = auth_headers("alice@example.com")
    conversation = item(client.post(f"{API}/conversations", headers=headers, json={"title": "Q"}))

    response = client.post(
        f"{API}/conversations/{conversation['id']}/messages",
        headers=headers,
        json={"content": "Anything there?"},
    )

    assert response.status_code == 201
    answer = item(response)["assistant_message"]
    assert answer["content"] == Message.NO_RELEVANT_CONTEXT
    assert answer["citations"] == []
    assert chat_client.calls == []


def test_refresh_rotation_links_old_token_to_new_one(client, session_factory) -> None:
    credentials = {"email": "carol@example.com", "password": "CorrectHorse!42"}
    client.post(f"{API}/auth/signup", json={"name": "Carol", **credentials})
    token_mode = {"X-Auth-Mode": "token"}
    login = client.post(f"{API}/auth/login", json=credentials, headers=token_mode)
    old = item(login)["refresh_token"]

    response = client.post(
        f"{API}/auth/refresh", json={"refresh_token": old}, headers=token_mode
    )
    assert response.status_code == 200

    with session_factory() as db:
        tokens = db.scalars(select(RefreshToken)).all()
    revoked = [t for t in tokens if t.revoked_at is not None]
    active = [t for t in tokens if t.revoked_at is None]
    assert len(revoked) == 1 and len(active) == 1
    assert revoked[0].replaced_by_token_id == active[0].id
