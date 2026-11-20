"""Blackbox tests for TASK-0949: DM whispers come from the narration port, and a veto stops the action.

Every call goes through the gateway to the real The Watcher app, served on a loopback port.
The narration port is selected with `RUNEFOBLE_WATCHER_NARRATION_ENGINE`. With
`inference_worker`, The Watcher calls the real inference worker on a loopback port, and the
worker calls the loopback fake OpenAI server (the external model runtime). The campaign, the
session, the board and its token are set up through public routes only (Hard Invariant 7).
"""

from __future__ import annotations

import json
import time
from collections.abc import Iterator

import httpx
import pytest
from fastapi.testclient import TestClient
from gateway_api.main import app as gateway_app
from inference_worker import api as worker_api
from inference_worker.llm_factory import build_llm_port

from tests.helpers.fake_openai_server import FakeOpenAI
from tests.helpers.inference_worker_port import install_worker_port
from tests.helpers.live_services import serve
from tests.helpers.the_watcher_app import watcher_app
from tests.helpers.watcher_board import open_board_with_tokens
from tests.helpers.ws_identity import bearer
from tests.realtime_session import open_table

DM = "dm_dora"
PLAYER = "valeros"
MODEL_NARRATION = "The torches gutter. Something breathes behind the sealed door."
PAUSE_WINDOW_MS = 300


@pytest.fixture
def watcher_url(monkeypatch: pytest.MonkeyPatch) -> Iterator[str]:
    """Serve the real The Watcher app and point the gateway at it before the gateway starts."""
    monkeypatch.delenv("RUNEFOBLE_WATCHER_NARRATION_ENGINE", raising=False)
    with serve(watcher_app) as url:
        monkeypatch.setenv("RUNEFOBLE_WATCHER_URL", url)
        yield url


@pytest.fixture
def gateway(
    watcher_url: str,
    game_session_upstream: str,
    board_state_upstream: str,
    character_sheet_upstream: str,
    voice_agent_upstream: str,
) -> Iterator[TestClient]:
    with TestClient(gateway_app) as client:
        yield client


@pytest.fixture
def table(gateway: TestClient, game_session_upstream: str) -> tuple[str, str]:
    """A campaign with a DM and one player, and a session, created through public routes."""
    return open_table(gateway, game_session_upstream, DM, {PLAYER: "player"})


@pytest.fixture
def narrator_live(monkeypatch: pytest.MonkeyPatch, fake_llm: FakeOpenAI) -> Iterator[FakeOpenAI]:
    """The narration port is the real inference worker on loopback, over the fake model."""
    fake_llm.content = json.dumps(
        {
            "narration": MODEL_NARRATION,
            "sensory_details": ["cold air"],
            "suggested_dm_prompts": ["Ask who opens the door."],
        }
    )
    install_worker_port(monkeypatch, build_llm_port(fake_llm.settings()))
    with serve(worker_api.app) as url:
        monkeypatch.setenv("RUNEFOBLE_INFERENCE_URL", url)
        monkeypatch.setenv("RUNEFOBLE_WATCHER_NARRATION_ENGINE", "inference_worker")
        yield fake_llm


def _list(gateway: TestClient, campaign_id: str, session_id: str) -> dict:
    res = gateway.get(
        "/api/v1/watcher/whispers",
        params={"session_id": session_id, "campaign_id": campaign_id},
        headers=bearer(DM),
    )
    assert res.status_code == 200, res.text
    return res.json()


def _whispers(gateway: TestClient, campaign_id: str, session_id: str) -> list[dict]:
    return _list(gateway, campaign_id, session_id)["whispers"]


def _generate(client: TestClient | httpx.Client, campaign_id: str, session_id: str):
    return client.post(
        "/api/v1/watcher/whispers/generate",
        json={
            "session_id": session_id,
            "campaign_id": campaign_id,
            "scene_context": "A sealed crypt door",
            "location_type": "crypt",
            "threat_level": "hard",
        },
        headers=bearer(DM),
    )


def test_a_new_session_has_no_whispers_and_names_no_model(
    gateway: TestClient, table: tuple[str, str]
) -> None:
    campaign_id, session_id = table

    listed = _list(gateway, campaign_id, session_id)

    assert listed["whispers"] == []
    assert listed["total"] == 0
    assert listed["narration_engine"] == "none"


def test_generate_without_a_narration_engine_is_503_and_records_nothing(
    gateway: TestClient, table: tuple[str, str], watcher_url: str
) -> None:
    """The Watcher answers 503. The gateway maps an owner 5xx to 502 (service-client contract)."""
    campaign_id, session_id = table

    with httpx.Client(base_url=watcher_url) as owner:
        direct = _generate(owner, campaign_id, session_id)
    via_gateway = _generate(gateway, campaign_id, session_id)

    assert direct.status_code == 503, direct.text
    detail = direct.json()["detail"]
    assert detail["error"] == "backend_unavailable"
    assert detail["backend"] == "none"
    assert "narration" in detail["message"]
    assert via_gateway.status_code == 502, via_gateway.text
    assert via_gateway.json()["upstream"] == "the_watcher"
    assert _whispers(gateway, campaign_id, session_id) == []


def test_generate_with_the_worker_records_model_narration(
    gateway: TestClient, table: tuple[str, str], narrator_live: FakeOpenAI
) -> None:
    campaign_id, session_id = table

    res = _generate(gateway, campaign_id, session_id)

    assert res.status_code == 200, res.text
    generated = res.json()
    assert [w["content"] for w in generated] == [MODEL_NARRATION]
    assert all(w["whisper_type"] == "narration" for w in generated)
    assert all(w["metadata"]["source"] == "llm" for w in generated)
    assert len(narrator_live.requests) == 1
    assert "sealed crypt door" in narrator_live.user_prompts()[0].lower()
    listed = _list(gateway, campaign_id, session_id)
    assert [w["whisper_id"] for w in listed["whispers"]] == [w["whisper_id"] for w in generated]
    assert listed["narration_engine"] == "inference_worker"


def test_a_player_cannot_generate_whispers(
    gateway: TestClient, table: tuple[str, str], narrator_live: FakeOpenAI
) -> None:
    campaign_id, session_id = table

    res = gateway.post(
        "/api/v1/watcher/whispers/generate",
        json={"session_id": session_id, "campaign_id": campaign_id},
        headers=bearer(PLAYER),
    )

    assert res.status_code == 403, res.text
    assert narrator_live.requests == []


def _token_position(gateway: TestClient, session_id: str) -> tuple[int, int]:
    board = gateway.get(f"/api/v1/boards/{session_id}", headers=bearer(DM))
    assert board.status_code == 200, board.text
    token = board.json()["tokens"]["tok-goblin"]
    return token["x"], token["y"]


def test_a_dm_veto_stops_the_action_and_a_player_veto_is_refused(
    gateway: TestClient, table: tuple[str, str], board_state_upstream: str
) -> None:
    campaign_id, session_id = table
    open_board_with_tokens(
        board_state_upstream,
        session_id,
        campaign_id,
        owner=DM,
        cols=10,
        rows=10,
        tokens=[{"token_id": "tok-goblin", "name": "Goblin", "x": 2, "y": 2}],
    )
    proposed = gateway.post(
        "/api/v1/watcher/actions/propose",
        json={
            "session_id": session_id,
            "campaign_id": campaign_id,
            "actor_name": "Goblin",
            "action_type": "move",
            "description": "The goblin runs to the door",
            "target": "tok-goblin",
            "parameters": {"x": 7, "y": 7},
            "pause_window_ms": PAUSE_WINDOW_MS,
        },
        headers=bearer(DM),
    )
    assert proposed.status_code == 200, proposed.text
    veto = {
        "session_id": session_id,
        "campaign_id": campaign_id,
        "action_id": proposed.json()["action_id"],
        "reason": "DM one-click veto",
    }

    refused = gateway.post("/api/v1/watcher/veto", json=veto, headers=bearer(PLAYER))
    vetoed = gateway.post("/api/v1/watcher/veto", json=veto, headers=bearer(DM))
    time.sleep(PAUSE_WINDOW_MS / 1000 + 0.3)

    assert refused.status_code == 403, refused.text
    assert vetoed.status_code == 200, vetoed.text
    assert vetoed.json()["status"] == "vetoed"
    pending = gateway.get(
        "/api/v1/watcher/actions/pending",
        params={"session_id": session_id, "campaign_id": campaign_id},
        headers=bearer(DM),
    )
    assert pending.status_code == 200, pending.text
    assert [a["status"] for a in pending.json()] == ["vetoed"]
    assert _token_position(gateway, session_id) == (2, 2)
