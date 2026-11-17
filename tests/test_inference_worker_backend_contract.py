"""Blackbox contract: the worker calls an OpenAI-compatible backend with its configured secret.

The fake backend is a real HTTP server on localhost. It stands in for the external model
runtime, which is a true process boundary. The worker is driven only through its public
HTTP route.
"""

import json
import threading
from collections.abc import Iterator
from http.server import BaseHTTPRequestHandler, HTTPServer
from typing import Any

import pytest
from httpx import ASGITransport, AsyncClient
from inference_worker import api
from inference_worker.api import app
from inference_worker.config import WorkerSettings
from inference_worker.llm_client import MultiBackendLLMClient
from pydantic import SecretStr

INTENT_CONTENT = json.dumps(
    {
        "action_type": "attack",
        "target_token_id": "tok-skel-1",
        "confidence": 0.9,
    }
)


class _RecordingHandler(BaseHTTPRequestHandler):
    captured: list[dict[str, Any]] = []

    def do_POST(self) -> None:  # noqa: N802 - stdlib handler naming
        length = int(self.headers.get("Content-Length", "0"))
        body = json.loads(self.rfile.read(length) or b"{}")
        self.captured.append(
            {
                "path": self.path,
                "authorization": self.headers.get("Authorization"),
                "body": body,
            }
        )
        reply = {
            "id": "chatcmpl-test",
            "object": "chat.completion",
            "created": 0,
            "model": body.get("model", ""),
            "choices": [
                {
                    "index": 0,
                    "message": {"role": "assistant", "content": INTENT_CONTENT},
                    "finish_reason": "stop",
                }
            ],
            "usage": {"prompt_tokens": 1, "completion_tokens": 1, "total_tokens": 2},
        }
        payload = json.dumps(reply).encode()
        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(payload)))
        self.end_headers()
        self.wfile.write(payload)

    def log_message(self, format: str, *args: Any) -> None:  # noqa: A002 - stdlib signature
        return


@pytest.fixture
def fake_backend() -> Iterator[tuple[str, list[dict[str, Any]]]]:
    captured: list[dict[str, Any]] = []
    handler = type("Handler", (_RecordingHandler,), {"captured": captured})
    server = HTTPServer(("127.0.0.1", 0), handler)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    try:
        host, port = server.server_address[:2]
        yield f"http://{host}:{port}/v1", captured
    finally:
        server.shutdown()
        server.server_close()


@pytest.mark.asyncio
async def test_intent_route_calls_openai_backend_with_configured_secret(
    monkeypatch: pytest.MonkeyPatch,
    fake_backend: tuple[str, list[dict[str, Any]]],
) -> None:
    base_url, captured = fake_backend
    settings = WorkerSettings(
        backend="openai_compatible",
        openai_base_url=base_url,
        openai_api_key=SecretStr("sk-contract-test"),
        openai_model="contract-model",
        max_tokens=256,
    )
    monkeypatch.setattr(api, "llm_client", MultiBackendLLMClient(settings))
    monkeypatch.setattr(api, "intent_graph", None)

    payload = {
        "campaign_id": "camp-test",
        "session_id": "sess-test",
        "speaker_id": "usr-test",
        "speaker_name": "Merisiel",
        "transcript": "I attack the skeleton with my rapier",
        "visible_tokens": [
            {"token_id": "tok-skel-1", "name": "Skeleton", "token_type": "monster", "x": 3, "y": 4}
        ],
    }
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        resp = await ac.post("/inference/v1/intent", json=payload)

    assert resp.status_code == 200
    data = resp.json()
    assert data["source"] == "llm"
    assert data["degraded"] is False
    assert data["action"]["action_type"] == "attack"

    assert len(captured) == 1
    call = captured[0]
    assert call["path"].endswith("/chat/completions")
    assert call["authorization"] == "Bearer sk-contract-test"
    assert call["body"]["model"] == "contract-model"
    assert call["body"]["max_completion_tokens"] == 256
