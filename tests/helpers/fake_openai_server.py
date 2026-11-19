"""Loopback OpenAI-compatible chat server for inference worker tests.

The worker reaches this server through its public `openai_compatible` backend. The server is a
true process boundary: it stands in for the external model runtime. It replies with the content
that a test sets, and it records each request body so a test can read the prompts the worker sent.
No code under test is replaced.
"""

from __future__ import annotations

import json
import threading
from collections.abc import Iterator
from contextlib import contextmanager
from dataclasses import dataclass, field
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from typing import Any

import pytest
from inference_worker.config import WorkerSettings


@dataclass
class FakeOpenAI:
    """The state of one fake server. Set `status` and `content` before a request."""

    base_url: str = ""
    status: int = 200
    content: str = "{}"
    requests: list[dict[str, Any]] = field(default_factory=list)

    def settings(self, **overrides: Any) -> WorkerSettings:
        """Worker settings that point the `openai_compatible` backend at this server."""
        values: dict[str, Any] = {
            "backend": "openai_compatible",
            "openai_base_url": self.base_url,
            "timeout_seconds": 5.0,
        }
        values.update(overrides)
        return WorkerSettings(**values)

    def user_prompts(self) -> list[str]:
        """Every user message the worker sent, in request order."""
        return [
            str(message["content"])
            for request in self.requests
            for message in request.get("messages", [])
            if message.get("role") == "user"
        ]


class _Server(ThreadingHTTPServer):
    def __init__(self, state: FakeOpenAI) -> None:
        super().__init__(("127.0.0.1", 0), _Handler)
        self.state = state


class _Handler(BaseHTTPRequestHandler):
    def do_POST(self) -> None:  # noqa: N802 - http.server naming
        length = int(self.headers.get("Content-Length", "0"))
        body = json.loads(self.rfile.read(length) or b"{}")
        state: FakeOpenAI = self.server.state  # type: ignore[attr-defined]
        state.requests.append(body)
        if state.status != 200:
            self._send(state.status, {"error": {"message": "fake failure", "type": "invalid"}})
            return
        self._send(200, _chat_completion(state.content, body.get("model", "")))

    def _send(self, status: int, document: dict[str, Any]) -> None:
        payload = json.dumps(document).encode()
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(payload)))
        self.end_headers()
        self.wfile.write(payload)

    def log_message(self, format: str, *args: Any) -> None:  # noqa: A002 - stdlib signature
        return


def _chat_completion(content: str, model: str) -> dict[str, Any]:
    return {
        "id": "fake-1",
        "object": "chat.completion",
        "created": 0,
        "model": model,
        "choices": [
            {
                "index": 0,
                "message": {"role": "assistant", "content": content},
                "finish_reason": "stop",
            }
        ],
        "usage": {"prompt_tokens": 1, "completion_tokens": 1, "total_tokens": 2},
    }


@contextmanager
def fake_openai_server() -> Iterator[FakeOpenAI]:
    """Serve one fake OpenAI-compatible chat endpoint on a free loopback port."""
    server = _Server(FakeOpenAI())
    server.state.base_url = f"http://127.0.0.1:{server.server_address[1]}/v1"
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    try:
        yield server.state
    finally:
        server.shutdown()
        server.server_close()


@pytest.fixture
def fake_llm() -> Iterator[FakeOpenAI]:
    with fake_openai_server() as state:
        yield state
