"""Blackbox tests for the inference worker failure contract and response provenance.

The worker and The Watcher run as real HTTP servers in this process. The LLM backend is a
fake OpenAI-compatible server, which is a true process boundary. No code under test is mocked.
Model output that is unusable fails the request with 503. No substitute output is returned.
"""

import os
from typing import Any

import pytest
from fastapi import FastAPI
from httpx import ASGITransport, AsyncClient
from inference_worker import api
from inference_worker.config import WorkerSettings
from inference_worker.llm_factory import build_llm_port
from runefoble_platform.service_credential import SERVICE_CREDENTIAL_HEADER

from tests.helpers.inference_worker_port import install_worker_port
from tests.helpers.live_services import closed_port_url, serve
from tests.helpers.spicedb_factory import make_table_runner
from tests.helpers.the_watcher_app import watcher_app
from tests.helpers.watcher_engine import error_fields, select_worker_engine
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
    """Point the worker app at a backend. Graphs are rebuilt for that port."""

    def _use(settings: WorkerSettings) -> None:
        install_worker_port(monkeypatch, build_llm_port(settings))

    return _use


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
async def test_model_output_with_action_reports_llm_source(use_worker_backend, fake_llm):
    fake_llm.content = '{"action_type": "dodge", "narrative_flavor": "Merisiel ducks low."}'
    use_worker_backend(fake_llm.settings())

    async with AsyncClient(
        transport=ASGITransport(app=api.app), base_url="http://test", headers=WORKER_AUTH
    ) as ac:
        resp = await ac.post("/inference/v1/intent", json=INTENT_PAYLOAD)

    assert resp.status_code == 200
    body = resp.json()
    assert body["source"] == "llm"
    assert body["action"]["action_type"] == "dodge"


@pytest.mark.asyncio
async def test_unusable_intent_output_is_503_not_a_heuristic_action(use_worker_backend, fake_llm):
    """Prose without an action_type fails the request. No keyword rule supplies an action."""
    fake_llm.content = "I cannot comply."
    use_worker_backend(fake_llm.settings())

    async with AsyncClient(
        transport=ASGITransport(app=api.app), base_url="http://test", headers=WORKER_AUTH
    ) as ac:
        resp = await ac.post("/inference/v1/intent", json=INTENT_PAYLOAD)

    assert resp.status_code == 503
    assert resp.json() == {"error": "backend_unavailable", "backend": "openai_compatible"}


@pytest.mark.asyncio
async def test_unusable_narration_output_is_503_not_canned_text(use_worker_backend, fake_llm):
    fake_llm.content = "no json here"
    use_worker_backend(fake_llm.settings())

    async with AsyncClient(
        transport=ASGITransport(app=api.app), base_url="http://test", headers=WORKER_AUTH
    ) as ac:
        resp = await ac.post("/inference/v1/dm-narration", json=NARRATION_PAYLOAD)

    assert resp.status_code == 503
    assert resp.json() == {"error": "backend_unavailable", "backend": "openai_compatible"}


@pytest.mark.asyncio
async def test_failing_model_server_returns_503(use_worker_backend, fake_llm):
    fake_llm.status = 400
    use_worker_backend(fake_llm.settings())

    async with AsyncClient(
        transport=ASGITransport(app=api.app), base_url="http://test", headers=WORKER_AUTH
    ) as ac:
        resp = await ac.post("/inference/v1/stand-in-action", json=STAND_IN_PAYLOAD)

    assert resp.status_code == 503
    assert resp.json() == {"error": "backend_unavailable", "backend": "openai_compatible"}


@pytest.mark.asyncio
async def test_model_server_500_returns_503(use_worker_backend, fake_llm):
    """A model server that answers 500 is an unavailable backend: the worker answers 503."""
    fake_llm.status = 500
    use_worker_backend(fake_llm.settings())

    async with AsyncClient(
        transport=ASGITransport(app=api.app), base_url="http://test", headers=WORKER_AUTH
    ) as ac:
        resp = await ac.post("/inference/v1/intent", json=INTENT_PAYLOAD)

    assert resp.status_code == 503
    assert resp.json() == {"error": "backend_unavailable", "backend": "openai_compatible"}


@pytest.mark.asyncio
@pytest.mark.parametrize("raw_body", [b"not json{", b'{"id": "no-choices"}'])
async def test_undecodable_model_server_body_is_500_not_503(use_worker_backend, fake_llm, raw_body):
    """A body the client library cannot decode is a defect, not an outage. It is never a 503."""
    fake_llm.raw_body = raw_body
    use_worker_backend(fake_llm.settings())

    async with AsyncClient(
        transport=ASGITransport(app=api.app, raise_app_exceptions=False),
        base_url="http://test",
        headers=WORKER_AUTH,
    ) as ac:
        resp = await ac.post("/inference/v1/intent", json=INTENT_PAYLOAD)

    assert resp.status_code == 500


@pytest.mark.asyncio
async def test_watcher_speech_surfaces_worker_503(use_worker_backend, monkeypatch, fake_llm):
    """The Watcher returns its own 503 when the worker reports backend_unavailable."""
    await make_table_runner("user-1", "sess-1", "camp-1")
    fake_llm.status = 400
    use_worker_backend(fake_llm.settings())
    speech_payload = {
        "speaker_id": "user-1",
        "speaker_name": "Valeros",
        "transcript": "I strike the goblin with my sword",
        "session_id": "sess-1",
        "campaign_id": "camp-1",
    }

    with serve(api.app) as worker_url, serve(_empty_board_app()) as board_url:
        select_worker_engine(monkeypatch, worker_url)
        monkeypatch.setenv("RUNEFOBLE_BOARD_STATE_URL", board_url)
        async with AsyncClient(
            transport=ASGITransport(app=watcher_app), base_url="http://test", headers=WATCHER_AUTH
        ) as ac:
            resp = await ac.post("/api/v1/watcher/transcribe-and-act", json=speech_payload)

    assert resp.status_code == 503
    assert error_fields(resp.json()["detail"]) == {
        "error": "backend_unavailable",
        "backend": "openai_compatible",
    }


@pytest.mark.asyncio
async def test_watcher_speech_unreachable_worker_is_503_not_template(monkeypatch):
    """With the worker unreachable, The Watcher does not return a template reply."""
    await make_table_runner("user-1", "sess-1", "camp-1")
    select_worker_engine(monkeypatch, closed_port_url())
    speech_payload = {
        "speaker_id": "user-1",
        "speaker_name": "Valeros",
        "transcript": "I strike the goblin with my sword",
        "session_id": "sess-1",
        "campaign_id": "camp-1",
    }

    with serve(_empty_board_app()) as board_url:
        monkeypatch.setenv("RUNEFOBLE_BOARD_STATE_URL", board_url)
        async with AsyncClient(
            transport=ASGITransport(app=watcher_app), base_url="http://test", headers=WATCHER_AUTH
        ) as ac:
            resp = await ac.post("/api/v1/watcher/transcribe-and-act", json=speech_payload)

    assert resp.status_code == 503
    assert error_fields(resp.json()["detail"]) == {
        "error": "backend_unavailable",
        "backend": "inference_worker",
    }


def _empty_board_app() -> FastAPI:
    """Fake board state service with a board that has no tokens."""
    app = FastAPI()

    @app.get("/api/v1/boards/{session_id}")
    async def _board(session_id: str) -> dict[str, Any]:
        return {"session_id": session_id, "tokens": {}}

    return app
