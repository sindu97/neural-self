"""Ollama chat-completion client."""

import json
import logging
from collections.abc import Iterator
from typing import Protocol

import httpx

from neuralshelf.core.exceptions import LLMServiceError

logger = logging.getLogger(__name__)


class ChatClient(Protocol):
    """Anything that can complete a list of role/content chat messages."""

    model: str

    def chat(self, messages: list[dict[str, str]]) -> str: ...

    def stream_chat(self, messages: list[dict[str, str]]) -> Iterator[str]:
        """Yield the reply in text fragments as the model generates them."""
        ...


class OllamaChatClient:
    """Generate replies, complete or streamed, via Ollama's /api/chat."""

    def __init__(
        self,
        *,
        base_url: str,
        model: str,
        timeout_seconds: float,
        temperature: float = 0.2,
    ) -> None:
        self.base_url = base_url.rstrip("/")
        self.model = model
        self.timeout_seconds = timeout_seconds
        self.temperature = temperature

    def _payload(self, messages: list[dict[str, str]], *, stream: bool) -> dict:
        return {
            "model": self.model,
            "messages": messages,
            "stream": stream,
            # Hidden reasoning only adds latency for grounded Q&A.
            "think": False,
            "options": {"temperature": self.temperature},
        }

    def chat(self, messages: list[dict[str, str]]) -> str:
        try:
            response = httpx.post(
                f"{self.base_url}/api/chat",
                json=self._payload(messages, stream=False),
                timeout=self.timeout_seconds,
            )
            response.raise_for_status()
            content = response.json()["message"]["content"]
        except (httpx.HTTPError, KeyError, TypeError, ValueError) as exc:
            logger.exception("Ollama chat request failed.")
            raise LLMServiceError() from exc

        return content.strip()

    def stream_chat(self, messages: list[dict[str, str]]) -> Iterator[str]:
        """Stream the reply; Ollama sends one JSON object per line."""
        try:
            with httpx.stream(
                "POST",
                f"{self.base_url}/api/chat",
                json=self._payload(messages, stream=True),
                timeout=self.timeout_seconds,
            ) as response:
                response.raise_for_status()
                for line in response.iter_lines():
                    if not line:
                        continue
                    event = json.loads(line)
                    if "error" in event:
                        raise ValueError(event["error"])
                    fragment = event.get("message", {}).get("content", "")
                    if fragment:
                        yield fragment
                    if event.get("done"):
                        return
        except (httpx.HTTPError, KeyError, TypeError, ValueError) as exc:
            logger.exception("Ollama streaming chat request failed.")
            raise LLMServiceError() from exc
