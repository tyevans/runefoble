"""Blackbox tests for TASK-0609: The Watcher routes stop sending placeholders and report provenance.

The Watcher runs in-process through its public HTTP routes. The inference worker and the
board state service are fake HTTP servers on loopback ports. They are process boundaries.
Each fake records what The Watcher sends, so the tests assert on the wire payloads.
"""

from typing import Any

import pytest
from fastapi import FastAPI
from fastapi.responses import JSONResponse
from httpx import ASGITransport, AsyncClient
from runefoble_platform.redis_bus import RedisStreamsEventBus
from the_watcher.main import app as watcher_app

from tests.helpers.live_services import closed_port_url, serve
from tests.helpers.spicedb_factory import bind_character_owner, make_table_runner
from tests.helpers.watcher_engine import error_fields, select_worker_engine
from tests.helpers.ws_identity import SIGNING_ISSUER

pytestmark = pytest.mark.usefixtures("trusted_ws_issuer")
WATCHER_CALLER = "test-user"

WORKER_503 = {"error": "backend_unavailable", "backend": "openai_compatible"}

STAND_IN_PAYLOAD: dict[str, Any] = {
    "character_name": "Kyra",
    "character_class": "Cleric",
    "penalties": ["drunk"],
    "scene_context": "Orc raiders attacking bridge",
    "personality_traits": ["valiant"],
    "session_id": "sess-1",
    "campaign_id": "camp-1",
}
NARRATE_PAYLOAD: dict[str, Any] = {
    "session_id": "sess-1",
    "campaign_id": "camp-1",
    "prompt": "Thunder echoes",
    "scene_environment": "Forgotten Library",
    "tone": "tense_mystery",
}
SPEECH_PAYLOAD: dict[str, Any] = {
    "speaker_id": "user-1",
    "speaker_name": "Valeros",
    "transcript": "I strike the goblin with my sword",
    "session_id": "sess-1",
    "campaign_id": "camp-1",
}
BOARD_TOKENS: dict[str, Any] = {
    "tok-valeros": {
        "token_id": "tok-valeros",
        "name": "Valeros",
        "token_type": "pc",
        "x": 2,
        "y": 3,
        "hp": 20,
        "is_friendly": True,
    },
    "tok-goblin": {
        "token_id": "tok-goblin",
        "name": "Goblin",
        "token_type": "monster",
        "x": 4,
        "y": 3,
        "hp": 7,
        "is_friendly": False,
    },
}


@pytest.fixture
def bus(default_redis_event_bus) -> RedisStreamsEventBus:
    event_bus = default_redis_event_bus
    return event_bus


def _recording_worker(captured: list[dict[str, Any]], status: int, body: dict[str, Any]) -> FastAPI:
    """Fake inference worker. Records each request body and answers with a fixed status."""
    app = FastAPI()

    async def _answer(payload: dict[str, Any]) -> JSONResponse:
        captured.append(payload)
        return JSONResponse(body, status_code=status)

    app.post("/inference/v1/intent")(_answer)
    app.post("/inference/v1/dm-narration")(_answer)
    app.post("/inference/v1/stand-in-action")(_answer)
    return app


def _fake_board(tokens: dict[str, Any]) -> FastAPI:
    """Fake board state service. Serves one board for any session."""
    app = FastAPI()

    @app.get("/api/v1/boards/{session_id}")
    async def _board(session_id: str) -> dict[str, Any]:
        return {
            "board_id": "00000000-0000-0000-0000-000000000001",
            "session_id": session_id,
            "tokens": tokens,
        }

    return app


async def _post(path: str, payload: dict[str, Any]):
    if payload.get("speaker_id"):
        await bind_character_owner(WATCHER_CALLER, payload["speaker_id"])
    if payload.get("session_id") and payload.get("campaign_id"):
        # The caller is the table DM for the session, so both DM and participant routes allow it.
        await make_table_runner(WATCHER_CALLER, payload["session_id"], payload["campaign_id"])
    headers = {"Authorization": f"Bearer {SIGNING_ISSUER.mint(WATCHER_CALLER)}"}
    async with AsyncClient(
        transport=ASGITransport(app=watcher_app), base_url="http://test", headers=headers
    ) as ac:
        return await ac.post(path, json=payload)


# ---------------------------------------------------------------------------
# Required ids and scene data (no placeholders)
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_stand_in_act_without_campaign_id_is_422(bus):
    payload = {k: v for k, v in STAND_IN_PAYLOAD.items() if k != "campaign_id"}
    resp = await _post("/api/v1/watcher/stand-in/act", payload)
    assert resp.status_code == 422


@pytest.mark.asyncio
async def test_stand_in_act_without_session_id_is_422(bus):
    payload = {k: v for k, v in STAND_IN_PAYLOAD.items() if k != "session_id"}
    resp = await _post("/api/v1/watcher/stand-in/act", payload)
    assert resp.status_code == 422


@pytest.mark.asyncio
async def test_narrate_without_campaign_id_is_422(bus):
    payload = {k: v for k, v in NARRATE_PAYLOAD.items() if k != "campaign_id"}
    resp = await _post("/api/v1/watcher/narrate", payload)
    assert resp.status_code == 422


@pytest.mark.asyncio
async def test_narrate_without_scene_environment_is_422(bus):
    payload = {k: v for k, v in NARRATE_PAYLOAD.items() if k != "scene_environment"}
    resp = await _post("/api/v1/watcher/narrate", payload)
    assert resp.status_code == 422


# ---------------------------------------------------------------------------
# Worker failure surfaces as 503, never as canned output with HTTP 200
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_stand_in_act_surfaces_worker_503(bus, monkeypatch):
    captured: list[dict[str, Any]] = []
    with serve(_recording_worker(captured, 503, WORKER_503)) as worker_url:
        select_worker_engine(monkeypatch, worker_url)
        resp = await _post("/api/v1/watcher/stand-in/act", STAND_IN_PAYLOAD)

    assert resp.status_code == 503
    assert error_fields(resp.json()["detail"]) == WORKER_503
    assert captured[0]["campaign_id"] == "camp-1"
    assert captured[0]["session_id"] == "sess-1"


@pytest.mark.asyncio
async def test_stand_in_act_unreachable_worker_is_503(bus, monkeypatch):
    select_worker_engine(monkeypatch, closed_port_url())
    resp = await _post("/api/v1/watcher/stand-in/act", STAND_IN_PAYLOAD)

    assert resp.status_code == 503
    assert error_fields(resp.json()["detail"]) == {
        "error": "backend_unavailable",
        "backend": "inference_worker",
    }


@pytest.mark.asyncio
async def test_narrate_surfaces_worker_503(bus, monkeypatch):
    captured: list[dict[str, Any]] = []
    with serve(_recording_worker(captured, 503, WORKER_503)) as worker_url:
        select_worker_engine(monkeypatch, worker_url)
        resp = await _post("/api/v1/watcher/narrate", NARRATE_PAYLOAD)

    assert resp.status_code == 503
    assert error_fields(resp.json()["detail"]) == WORKER_503
    assert "narrative" not in resp.json()


@pytest.mark.asyncio
async def test_narrate_unreachable_worker_is_503_not_canned_text(bus, monkeypatch):
    select_worker_engine(monkeypatch, closed_port_url())
    resp = await _post("/api/v1/watcher/narrate", NARRATE_PAYLOAD)

    assert resp.status_code == 503
    assert resp.json()["detail"]["error"] == "backend_unavailable"


@pytest.mark.asyncio
async def test_narrate_with_heuristic_engine_is_503(bus, monkeypatch):
    monkeypatch.setenv("RUNEFOBLE_WATCHER_ENGINE", "heuristic")
    resp = await _post("/api/v1/watcher/narrate", NARRATE_PAYLOAD)

    assert resp.status_code == 503
    assert resp.json()["detail"]["error"] == "backend_unavailable"


@pytest.mark.asyncio
async def test_narrate_passes_scene_data_and_reports_provenance(bus, monkeypatch):
    captured: list[dict[str, Any]] = []
    body = {
        "session_id": "sess-1",
        "narration": "Pages turn by themselves.",
        "sensory_details": ["dust"],
        "suggested_dm_prompts": ["Ask who turned the page."],
        "tension_level": "rising",
        "source": "llm",
        "degraded": False,
    }
    with serve(_recording_worker(captured, 200, body)) as worker_url:
        select_worker_engine(monkeypatch, worker_url)
        resp = await _post("/api/v1/watcher/narrate", NARRATE_PAYLOAD)

    assert resp.status_code == 200
    assert captured[0]["scene_environment"] == "Forgotten Library"
    assert captured[0]["tone"] == "tense_mystery"
    assert captured[0]["campaign_id"] == "camp-1"
    data = resp.json()
    assert data["narrative"] == "Pages turn by themselves."
    assert data["source"] == "llm"
    assert data["degraded"] is False


# ---------------------------------------------------------------------------
# Speech path: real visible tokens, nullable confidence, passed-through provenance
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_speech_sends_board_tokens_and_reports_worker_provenance(bus, monkeypatch):
    captured: list[dict[str, Any]] = []
    action = {"action_type": "attack", "target_token_name": "Goblin", "narrative_flavor": "Strike!"}
    body = {
        "session_id": "sess-1",
        "speaker_name": "Valeros",
        "action": action,
        "execution_time_ms": 1.0,
        "source": "llm",
        "degraded": False,
    }
    with (
        serve(_recording_worker(captured, 200, body)) as worker_url,
        serve(_fake_board(BOARD_TOKENS)) as board_url,
    ):
        select_worker_engine(monkeypatch, worker_url)
        monkeypatch.setenv("RUNEFOBLE_BOARD_STATE_URL", board_url)
        resp = await _post("/api/v1/watcher/transcribe-and-act", SPEECH_PAYLOAD)

    assert resp.status_code == 200
    sent = {t["token_id"]: t for t in captured[0]["visible_tokens"]}
    assert set(sent) == {"tok-valeros", "tok-goblin"}
    assert sent["tok-goblin"]["x"] == 4 and sent["tok-goblin"]["token_type"] == "monster"
    data = resp.json()
    assert data["action_type"] == "attack"
    assert data["confidence"] is None
    assert data["source"] == "llm"
    assert data["degraded"] is False


@pytest.mark.asyncio
async def test_speech_board_unavailable_is_503_and_worker_not_called(bus, monkeypatch):
    captured: list[dict[str, Any]] = []
    body = {
        "session_id": "sess-1",
        "speaker_name": "Valeros",
        "action": {"action_type": "attack"},
        "source": "llm",
        "degraded": False,
    }
    with serve(_recording_worker(captured, 200, body)) as worker_url:
        select_worker_engine(monkeypatch, worker_url)
        monkeypatch.setenv("RUNEFOBLE_BOARD_STATE_URL", closed_port_url())
        resp = await _post("/api/v1/watcher/transcribe-and-act", SPEECH_PAYLOAD)

    assert resp.status_code == 503
    assert resp.json()["detail"] == {"error": "backend_unavailable", "backend": "board_state"}
    assert captured == []
