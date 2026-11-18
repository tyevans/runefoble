"""Blackbox tests for the inference worker failure contract and response provenance.

The worker and The Watcher run as real HTTP servers in this process. The LLM backend is a
fake OpenAI-compatible server, which is a true process boundary. No code under test is mocked.
"""

import json
import os
import threading
from collections.abc import Iterator
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from typing import Any

import pytest
from fastapi import FastAPI
from httpx import ASGITransport, AsyncClient
from inference_worker import api
from inference_worker.config import WorkerSettings
from inference_worker.llm_client import MultiBackendLLMClient
from runefoble_platform.service_credential import SERVICE_CREDENTIAL_HEADER
from the_watcher.main import app as watcher_app
from the_watcher.routers.intent import speech

from tests.helpers.live_services import closed_port_url, serve
from tests.helpers.ws_identity import SIGNING_ISSUER

WORKER_AUTH = {SERVICE_CREDENTIAL_HEADER: os.environ["RUNEFOBLE_SERVICE_CREDENTIAL"]}
WATCHER_AUTH = {"Authorization": f"Bearer {SIGNING_ISSUER.mint('user-1')}"}
pytestmark = pytest.mark.usefixtures("trusted_ws_issuer")

INTENT_PAYLOAD: dict[str, Any] = {
    "campaign_id": "camp-1",
    "session_id": "sess-1",
    "speaker_id": "spk-1",
    "speaker_name": "Merisiel",
    "transcript": "I attack the skeleton with my rapier",
    "visible_tokens": [],
}
NARRATION_PAYLOAD: dict[str, Any] = {
    "campaign_id": "camp-1",
    "session_id": "sess-1",
    "scene_environment": "Forgotten Library",
    "guidance_prompt": "What do the adventurers see?",
}
STAND_IN_PAYLOAD: dict[str, Any] = {
    "campaign_id": "camp-1",
    "session_id": "sess-1",
    "character_name": "Seoni",
    "character_class": "Sorcerer",
    "penalties": ["drunk"],
    "visible_enemies": ["Orc Chieftain"],
}
ENDPOINTS = [
    ("/inference/v1/intent", INTENT_PAYLOAD),
    ("/inference/v1/dm-narration", NARRATION_PAYLOAD),
    ("/inference/v1/stand-in-action", STAND_IN_PAYLOAD),
]


@pytest.fixture
def use_worker_backend(monkeypatch: pytest.MonkeyPatch):
    """Point the worker app at a backend. Graphs are rebuilt for that client."""

    def _use(settings: WorkerSettings) -> None:
        monkeypatch.setattr(api, "llm_client", MultiBackendLLMClient(settings))
        monkeypatch.setattr(api, "intent_graph", None)
        monkeypatch.setattr(api, "narration_graph", None)
        monkeypatch.setattr(api, "stand_in_graph", None)

    return _use


class _FakeLLMHandler(BaseHTTPRequestHandler):
    """Minimal OpenAI-compatible chat endpoint. Reply content comes from the server state."""

    def do_POST(self) -> None:  # noqa: N802 - http.server naming
        length = int(self.headers.get("Content-Length", "0"))
        self.rfile.read(length)
        state = self.server.reply  # type: ignore[attr-defined]
        if state.get("status", 200) != 200:
            body = json.dumps({"error": {"message": "fake failure", "type": "invalid"}})
            self._send(state["status"], body)
            return
        body = json.dumps(
            {
                "id": "fake-1",
                "object": "chat.completion",
                "created": 0,
                "model": "fake",
                "choices": [
                    {
                        "index": 0,
                        "message": {"role": "assistant", "content": state["content"]},
                        "finish_reason": "stop",
                    }
                ],
                "usage": {"prompt_tokens": 1, "completion_tokens": 1, "total_tokens": 2},
            }
        )
        self._send(200, body)

    def _send(self, status: int, body: str) -> None:
        payload = body.encode()
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(payload)))
        self.end_headers()
        self.wfile.write(payload)

    def log_message(self, format: str, *args: Any) -> None:  # noqa: A002
        return


@pytest.fixture
def fake_llm() -> Iterator[ThreadingHTTPServer]:
    server = ThreadingHTTPServer(("127.0.0.1", 0), _FakeLLMHandler)
    server.reply = {"status": 200, "content": "{}"}  # type: ignore[attr-defined]
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    try:
        yield server
    finally:
        server.shutdown()
        server.server_close()


def _llm_settings(server: ThreadingHTTPServer) -> WorkerSettings:
    port = server.server_address[1]
    return WorkerSettings(
        backend="openai_compatible",
        openai_base_url=f"http://127.0.0.1:{port}/v1",
        timeout_seconds=5.0,
    )


@pytest.mark.asyncio
@pytest.mark.parametrize(("path", "payload"), ENDPOINTS)
async def test_unreachable_backend_returns_explicit_503(use_worker_backend, path, payload):
    """A real backend that cannot be reached returns 503, never a success body."""
    unreachable = WorkerSettings(
        backend="openai_compatible",
        openai_base_url=f"{closed_port_url()}/v1",
        timeout_seconds=2.0,
    )
    use_worker_backend(unreachable)

    async with AsyncClient(
        transport=ASGITransport(app=api.app), base_url="http://test", headers=WORKER_AUTH
    ) as ac:
        resp = await ac.post(path, json=payload)

    assert resp.status_code == 503
    assert resp.json() == {"error": "backend_unavailable", "backend": "openai_compatible"}


@pytest.mark.asyncio
async def test_auto_backend_without_server_is_unavailable(use_worker_backend):
    """Auto mode never selects mock by itself. No detected server means 503."""
    use_worker_backend(WorkerSettings(backend="auto", openai_base_url="http://127.0.0.1:9/v1"))

    async with AsyncClient(
        transport=ASGITransport(app=api.app), base_url="http://test", headers=WORKER_AUTH
    ) as ac:
        resp = await ac.post("/inference/v1/intent", json=INTENT_PAYLOAD)

    assert resp.status_code == 503
    assert resp.json()["error"] == "backend_unavailable"


@pytest.mark.asyncio
async def test_explicit_mock_backend_reports_mock_source(use_worker_backend):
    use_worker_backend(WorkerSettings(backend="mock"))

    async with AsyncClient(
        transport=ASGITransport(app=api.app), base_url="http://test", headers=WORKER_AUTH
    ) as ac:
        intent = await ac.post("/inference/v1/intent", json=INTENT_PAYLOAD)
        narration = await ac.post("/inference/v1/dm-narration", json=NARRATION_PAYLOAD)
        stand_in = await ac.post("/inference/v1/stand-in-action", json=STAND_IN_PAYLOAD)

    for resp in (intent, narration, stand_in):
        assert resp.status_code == 200
        assert resp.json()["source"] == "mock"
        assert resp.json()["degraded"] is False
    assert intent.json()["action"]["action_type"] == "attack"


@pytest.mark.asyncio
async def test_model_output_with_action_reports_llm_source(use_worker_backend, fake_llm):
    fake_llm.reply = {  # type: ignore[attr-defined]
        "status": 200,
        "content": '{"action_type": "dodge", "narrative_flavor": "Merisiel ducks low."}',
    }
    use_worker_backend(_llm_settings(fake_llm))

    async with AsyncClient(
        transport=ASGITransport(app=api.app), base_url="http://test", headers=WORKER_AUTH
    ) as ac:
        resp = await ac.post("/inference/v1/intent", json=INTENT_PAYLOAD)

    assert resp.status_code == 200
    body = resp.json()
    assert body["source"] == "llm"
    assert body["degraded"] is False
    assert body["action"]["action_type"] == "dodge"


@pytest.mark.asyncio
async def test_unusable_model_output_uses_regex_heuristic_and_is_degraded(
    use_worker_backend, fake_llm
):
    fake_llm.reply = {"status": 200, "content": "I cannot comply."}  # type: ignore[attr-defined]
    use_worker_backend(_llm_settings(fake_llm))

    async with AsyncClient(
        transport=ASGITransport(app=api.app), base_url="http://test", headers=WORKER_AUTH
    ) as ac:
        resp = await ac.post("/inference/v1/intent", json=INTENT_PAYLOAD)

    assert resp.status_code == 200
    body = resp.json()
    assert body["source"] == "heuristic"
    assert body["degraded"] is True
    assert body["action"]["action_type"] == "attack"


@pytest.mark.asyncio
async def test_unusable_narration_output_is_503_not_canned_text(use_worker_backend, fake_llm):
    fake_llm.reply = {"status": 200, "content": "no json here"}  # type: ignore[attr-defined]
    use_worker_backend(_llm_settings(fake_llm))

    async with AsyncClient(
        transport=ASGITransport(app=api.app), base_url="http://test", headers=WORKER_AUTH
    ) as ac:
        resp = await ac.post("/inference/v1/dm-narration", json=NARRATION_PAYLOAD)

    assert resp.status_code == 503
    assert resp.json() == {"error": "backend_unavailable", "backend": "openai_compatible"}


@pytest.mark.asyncio
async def test_failing_model_server_returns_503(use_worker_backend, fake_llm):
    fake_llm.reply = {"status": 400, "content": ""}  # type: ignore[attr-defined]
    use_worker_backend(_llm_settings(fake_llm))

    async with AsyncClient(
        transport=ASGITransport(app=api.app), base_url="http://test", headers=WORKER_AUTH
    ) as ac:
        resp = await ac.post("/inference/v1/stand-in-action", json=STAND_IN_PAYLOAD)

    assert resp.status_code == 503
    assert resp.json() == {"error": "backend_unavailable", "backend": "openai_compatible"}


@pytest.mark.asyncio
async def test_watcher_speech_surfaces_worker_503(use_worker_backend, monkeypatch, fake_llm):
    """The Watcher returns its own 503 when the worker reports backend_unavailable."""
    fake_llm.reply = {"status": 400, "content": ""}  # type: ignore[attr-defined]
    use_worker_backend(_llm_settings(fake_llm))
    speech_payload = {
        "speaker_id": "user-1",
        "speaker_name": "Valeros",
        "transcript": "I strike the goblin with my sword",
        "session_id": "sess-1",
        "campaign_id": "camp-1",
    }

    with serve(api.app) as worker_url, serve(_empty_board_app()) as board_url:
        monkeypatch.setattr(speech, "INFERENCE_URL", worker_url)
        monkeypatch.setattr(speech, "BOARD_STATE_URL", board_url)
        async with AsyncClient(
            transport=ASGITransport(app=watcher_app), base_url="http://test", headers=WATCHER_AUTH
        ) as ac:
            resp = await ac.post("/api/v1/watcher/intent", json=speech_payload)

    assert resp.status_code == 503
    assert resp.json()["detail"] == {"error": "backend_unavailable", "backend": "openai_compatible"}


@pytest.mark.asyncio
async def test_watcher_speech_unreachable_worker_is_503_not_template(monkeypatch):
    """With the worker unreachable, The Watcher does not return a template reply."""
    monkeypatch.setattr(speech, "INFERENCE_URL", closed_port_url())
    speech_payload = {
        "speaker_id": "user-1",
        "speaker_name": "Valeros",
        "transcript": "I strike the goblin with my sword",
        "session_id": "sess-1",
        "campaign_id": "camp-1",
    }

    with serve(_empty_board_app()) as board_url:
        monkeypatch.setattr(speech, "BOARD_STATE_URL", board_url)
        async with AsyncClient(
            transport=ASGITransport(app=watcher_app), base_url="http://test", headers=WATCHER_AUTH
        ) as ac:
            resp = await ac.post("/api/v1/watcher/intent", json=speech_payload)

    assert resp.status_code == 503
    assert resp.json()["detail"] == {"error": "backend_unavailable", "backend": "inference_worker"}


def _empty_board_app() -> FastAPI:
    """Fake board state service with a board that has no tokens."""
    app = FastAPI()

    @app.get("/api/v1/boards/{session_id}")
    async def _board(session_id: str) -> dict[str, Any]:
        return {"session_id": session_id, "tokens": {}}

    return app
