"""Streaming answers over Server-Sent Events."""

import json

import pytest
from sqlalchemy import func, select

from neuralshelf.core.exceptions import LLMServiceError
from neuralshelf.core.messages import Message
from neuralshelf.db.seeders.sample_pdf import make_pdf
from neuralshelf.features.chat.models import ChatMessage

pytestmark = pytest.mark.integration

API = "/api/v1"
TEXT = "Photosynthesis lets plants convert sunlight water and carbon dioxide into sugar."


def parse_sse(body: str) -> list[tuple[str, dict]]:
    events = []
    for block in body.strip().split("\n\n"):
        lines = dict(line.split(": ", 1) for line in block.splitlines())
        events.append((lines["event"], json.loads(lines["data"])))
    return events


@pytest.fixture
def headers(auth_headers):
    return auth_headers("stream@example.com")


@pytest.fixture
def conversation_url(client, headers):
    conversation = client.post(f"{API}/conversations", headers=headers).json()["data"][0]
    return f"{API}/conversations/{conversation['id']}"


@pytest.fixture
def ingested_document(client, headers, worker):
    response = client.post(
        f"{API}/documents",
        headers=headers,
        files={"file": ("bio.pdf", make_pdf([TEXT]), "application/pdf")},
    )
    worker.run_until_idle()
    return response.json()["data"][0]


def message_count(session_factory) -> int:
    with session_factory() as db:
        return db.scalar(select(func.count()).select_from(ChatMessage))


def test_stream_sends_start_tokens_and_done(
    client, headers, conversation_url, ingested_document, chat_client, session_factory
) -> None:
    response = client.post(
        f"{conversation_url}/messages/stream",
        headers=headers,
        json={"content": "What does photosynthesis do?"},
    )

    assert response.status_code == 200
    assert response.headers["content-type"].startswith("text/event-stream")
    events = parse_sse(response.text)
    names = [name for name, _ in events]
    assert names[0] == "start" and names[-1] == "done"
    assert set(names[1:-1]) == {"token"} and len(names) > 3

    start = events[0][1]
    assert start["citations"][0]["document_id"] == ingested_document["id"]

    streamed = "".join(data["delta"] for name, data in events if name == "token")
    done = events[-1][1]
    assert streamed == chat_client.answer
    assert done["assistant_message"]["content"] == chat_client.answer
    assert done["assistant_message"]["citations"][0]["filename"] == "bio.pdf"
    assert done["user_message"]["content"] == "What does photosynthesis do?"

    history = client.get(f"{conversation_url}/messages", headers=headers).json()
    assert [m["content"] for m in history["data"]] == [
        "What does photosynthesis do?",
        chat_client.answer,
    ]


def test_stream_without_relevant_documents(client, headers, conversation_url, chat_client) -> None:
    response = client.post(
        f"{conversation_url}/messages/stream", headers=headers, json={"content": "Anything?"}
    )

    events = parse_sse(response.text)
    assert [name for name, _ in events] == ["start", "token", "done"]
    assert events[-1][1]["assistant_message"]["content"] == Message.NO_RELEVANT_CONTEXT
    assert chat_client.calls == []


def test_errors_before_streaming_are_normal_json_responses(client, headers, auth_headers) -> None:
    other = auth_headers("someone-else@example.com")
    conversation = client.post(f"{API}/conversations", headers=other).json()["data"][0]

    response = client.post(
        f"{API}/conversations/{conversation['id']}/messages/stream",
        headers=headers,
        json={"content": "hi"},
    )

    assert response.status_code == 404
    assert response.json()["code"] == "CONVERSATION_NOT_FOUND"


def test_model_failure_mid_stream_sends_error_and_saves_nothing(
    client, headers, conversation_url, ingested_document, chat_client, session_factory
) -> None:
    def broken_stream(messages):
        yield "Partial "
        raise LLMServiceError()

    chat_client.stream_chat = broken_stream

    response = client.post(
        f"{conversation_url}/messages/stream", headers=headers, json={"content": "Explain"}
    )

    events = parse_sse(response.text)
    assert [name for name, _ in events] == ["start", "token", "error"]
    assert events[-1][1]["code"] == "LLM_SERVICE_UNAVAILABLE"
    assert message_count(session_factory) == 0
