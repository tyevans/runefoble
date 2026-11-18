"""Blackbox tests for TASK-0741: The Watcher selects its engines through ports.

The Watcher runs in-process through its public HTTP routes. Engine selection uses the public
settings `RUNEFOBLE_WATCHER_ENGINE` and `RUNEFOBLE_INFERENCE_URL`. The board state service is
a loopback HTTP fake, which is a process boundary. No private state is changed.
"""

import pytest
from fastapi import FastAPI
from httpx import ASGITransport, AsyncClient
from pydantic import ValidationError
from runefoble_platform.redis_bus import RedisStreamsEventBus
from starlette.testclient import TestClient
from the_watcher.main import app as watcher_app
from the_watcher.main import set_event_bus as watcher_set_event_bus

from tests.helpers.live_services import closed_port_url, serve
from tests.helpers.mock_redis import MockAsyncRedis
from tests.helpers.spicedb_factory import make_table_runner
from tests.helpers.ws_identity import SIGNING_ISSUER

pytestmark = pytest.mark.usefixtures("trusted_ws_issuer")

CALLER = "user-1"
SPEECH_PAYLOAD = {
    "speaker_id": CALLER,
    "speaker_name": "Valeros",
    "transcript": "I strike the goblin with my sword",
    "session_id": "sess-1",
    "campaign_id": "camp-1",
}


@pytest.fixture
def event_store() -> MockAsyncRedis:
    """Route The Watcher's published events into an in-memory stream store."""
    redis = MockAsyncRedis()
    watcher_set_event_bus(RedisStreamsEventBus(client=redis))
    return redis


def _empty_board() -> FastAPI:
    """Fake board state service with a board that has no tokens."""
    app = FastAPI()

    @app.get("/api/v1/boards/{session_id}")
    async def _board(session_id: str) -> dict[str, object]:
        return {"session_id": session_id, "tokens": {}}

    return app


async def _post_speech() -> object:
    await make_table_runner(CALLER, "sess-1", "camp-1")
    headers = {"Authorization": f"Bearer {SIGNING_ISSUER.mint(CALLER)}"}
    async with AsyncClient(
        transport=ASGITransport(app=watcher_app), base_url="http://test", headers=headers
    ) as ac:
        return await ac.post("/api/v1/watcher/transcribe-and-act", json=SPEECH_PAYLOAD)


@pytest.mark.asyncio
async def test_speech_with_worker_stopped_is_503_and_publishes_no_intent(event_store, monkeypatch):
    monkeypatch.setenv("RUNEFOBLE_WATCHER_ENGINE", "inference_worker")
    monkeypatch.setenv("RUNEFOBLE_INFERENCE_URL", closed_port_url())
    with serve(_empty_board()) as board_url:
        monkeypatch.setenv("RUNEFOBLE_BOARD_STATE_URL", board_url)
        resp = await _post_speech()

    assert resp.status_code == 503
    assert resp.json()["detail"]["error"] == "backend_unavailable"
    assert resp.json()["detail"]["backend"] == "inference_worker"
    assert not event_store.streams, "a failed engine must publish no intent or narration event"


@pytest.mark.asyncio
async def test_speech_with_explicit_heuristic_engine_needs_no_worker(event_store, monkeypatch):
    monkeypatch.setenv("RUNEFOBLE_WATCHER_ENGINE", "heuristic")
    monkeypatch.delenv("RUNEFOBLE_INFERENCE_URL", raising=False)
    with serve(_empty_board()) as board_url:
        monkeypatch.setenv("RUNEFOBLE_BOARD_STATE_URL", board_url)
        resp = await _post_speech()

    assert resp.status_code == 200
    assert resp.json()["action_type"] == "attack"


def test_start_up_with_inference_worker_and_no_url_fails(monkeypatch):
    monkeypatch.setenv("RUNEFOBLE_WATCHER_ENGINE", "inference_worker")
    monkeypatch.delenv("RUNEFOBLE_INFERENCE_URL", raising=False)

    with (
        pytest.raises(RuntimeError, match="RUNEFOBLE_INFERENCE_URL is not set"),
        TestClient(watcher_app),
    ):
        pass


def test_start_up_with_unknown_engine_value_fails(monkeypatch):
    monkeypatch.setenv("RUNEFOBLE_WATCHER_ENGINE", "regex")

    with pytest.raises(ValidationError, match="Input should be"), TestClient(watcher_app):
        pass
