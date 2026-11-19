"""Blackbox tests: gateway speak-and-act proxies to The Watcher intent route (TASK-0583).

The gateway verifies the caller and forwards the body and bearer token to `the_watcher`.
The Watcher owns intent parsing and runs as a live loopback upstream (ADR-0015). Setup runs
through public frontdoors only (ADR-0014, Hard Invariant 7).
"""

from __future__ import annotations

from collections.abc import Iterator
from typing import Any

import httpx
import pytest
from fastapi.testclient import TestClient
from gateway_api.main import app as gateway_app
from the_watcher.main import app as watcher_app

from tests.helpers.live_services import closed_port_url, serve
from tests.helpers.spectator_table import open_board_table
from tests.helpers.ws_identity import bearer

SPEAK_PATH = "/api/v1/watcher/speak-and-act"


@pytest.fixture
def watcher_url(monkeypatch: pytest.MonkeyPatch) -> Iterator[str]:
    """Serve the real The Watcher app and point the gateway at it before the gateway starts."""
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
    """The gateway, started after `watcher_url` is set, so its registry holds the Watcher URL."""
    with TestClient(gateway_app) as client:
        yield client


@pytest.fixture
def table(
    gateway: TestClient, game_session_upstream: str, board_state_upstream: str
) -> tuple[str, str]:
    """A campaign and board with one player, created through public routes."""
    return open_board_table(
        gateway, game_session_upstream, board_state_upstream, "dm_dora", {"valeros": "player"}
    )


def _speech(campaign_id: str, session_id: str, transcript: str) -> dict[str, Any]:
    return {
        "speaker_id": "valeros",
        "speaker_name": "Valeros",
        "transcript": transcript,
        "session_id": session_id,
        "campaign_id": campaign_id,
        "from_x": 5,
        "from_y": 5,
        "grid_cols": 12,
        "grid_rows": 12,
    }


def test_gateway_returns_the_watchers_parsed_intent_unchanged(
    gateway: TestClient, table: tuple[str, str], watcher_url: str
) -> None:
    """The gateway answers exactly what The Watcher answers for the same body and caller."""
    campaign_id, session_id = table
    body = _speech(campaign_id, session_id, "move three squares north")

    res = gateway.post(SPEAK_PATH, json=body, headers=bearer("valeros"))
    owner = httpx.post(f"{watcher_url}/api/v1/watcher/transcribe-and-act", json=body, headers=bearer("valeros"))

    assert res.status_code == owner.status_code == 200, res.text
    assert res.json() == owner.json()
    assert "stepped forward" not in res.text


def test_move_transcript_is_parsed_as_a_move(gateway: TestClient, table: tuple[str, str]) -> None:
    campaign_id, session_id = table
    body = _speech(campaign_id, session_id, "move 3 squares north")

    res = gateway.post(SPEAK_PATH, json=body, headers=bearer("valeros"))

    assert res.status_code == 200, res.text
    intent = res.json()
    assert intent["action_type"] == "move"
    assert intent["parameters"]["dy"] == -3


def test_missing_transcript_returns_the_watchers_422(
    gateway: TestClient, table: tuple[str, str]
) -> None:
    campaign_id, session_id = table
    body = _speech(campaign_id, session_id, "unused")
    del body["transcript"]

    res = gateway.post(SPEAK_PATH, json=body, headers=bearer("valeros"))

    assert res.status_code == 422
    assert "transcript" in res.text


def test_watcher_down_returns_503_naming_the_upstream(
    gateway: TestClient,
    table: tuple[str, str],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    campaign_id, session_id = table
    body = _speech(campaign_id, session_id, "move three squares north")
    monkeypatch.setenv("RUNEFOBLE_WATCHER_URL", closed_port_url())

    with TestClient(gateway_app) as client:
        res = client.post(SPEAK_PATH, json=body, headers=bearer("valeros"))

    assert res.status_code == 503
    assert res.json()["upstream"] == "the_watcher"
    assert "stepped forward" not in res.text


def test_speak_and_act_needs_a_verified_caller(gateway: TestClient, table: tuple[str, str]) -> None:
    campaign_id, session_id = table
    body = _speech(campaign_id, session_id, "move three squares north")

    assert gateway.post(SPEAK_PATH, json=body).status_code == 401
