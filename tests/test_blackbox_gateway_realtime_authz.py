"""Blackbox frontdoor tests for realtime, companion and signaling authorization (TASK-0544).

Governed by ADR-0001 (`session.observe`, `session.participate`, `session.control`) and
Hard Invariant 7. Setup runs through public frontdoors only. TASK-0770 covers `/ws/session`.
"""

from __future__ import annotations

from collections.abc import Iterator
from concurrent.futures import ThreadPoolExecutor
from concurrent.futures import TimeoutError as FutureTimeout
from typing import Any

import pytest
from fastapi.testclient import TestClient
from gateway_api.main import app as gateway_app
from starlette.testclient import WebSocketTestSession
from starlette.websockets import WebSocketDisconnect
from the_watcher.main import app as watcher_app

from tests.helpers.live_services import serve
from tests.helpers.ws_identity import ws_subprotocols
from tests.realtime_session import bearer, open_table

FORBIDDEN = 4403
SILENCE_SECONDS = 1.0


@pytest.fixture
def watcher_url(monkeypatch: pytest.MonkeyPatch) -> Iterator[str]:
    """Serve the real The Watcher app for speak-and-act (TASK-0583)."""
    with serve(watcher_app) as url:
        monkeypatch.setenv("RUNEFOBLE_WATCHER_URL", url)
        yield url


@pytest.fixture
def gateway(
    watcher_url: str,
    game_session_upstream: str,
    character_sheet_upstream: str,
    voice_agent_upstream: str,
) -> Iterator[TestClient]:
    """The gateway, started after `watcher_url` is set, so its registry holds the Watcher URL."""
    with TestClient(gateway_app) as client:
        yield client


@pytest.fixture
def table(gateway: TestClient, game_session_upstream: str) -> tuple[str, str]:
    """A campaign (campaign id, session id) with a DM, a player and a spectator."""
    return open_table(
        gateway,
        game_session_upstream,
        "dm_dora",
        {"player_pip": "player", "spectator_sol": "spectator"},
    )


def _refused_code(client: TestClient, path: str, user: str) -> int:
    with (
        pytest.raises(WebSocketDisconnect) as refused,
        client.websocket_connect(path, subprotocols=ws_subprotocols(user)) as ws,
    ):
        ws.receive_json()
    return refused.value.code


def _frame_within(ws: WebSocketTestSession, seconds: float) -> dict[str, Any] | None:
    pool = ThreadPoolExecutor(max_workers=1)
    pending = pool.submit(ws.receive_json)
    try:
        return pending.result(timeout=seconds)
    except FutureTimeout:
        return None
    finally:
        pool.shutdown(wait=False)


@pytest.mark.parametrize("path", ["/ws/voice/{sid}", "/ws/mobile-companion/{sid}"])
def test_signaling_and_companion_sockets_need_session_observe(gateway, table, path) -> None:
    _, session_id = table
    target = path.format(sid=session_id)

    assert _refused_code(gateway, target, "stranger_eve") == FORBIDDEN

    with gateway.websocket_connect(target, subprotocols=ws_subprotocols("player_pip")) as ws:
        assert ws.receive_json()["type"] in ("connected", "mobile_companion_connected")


@pytest.mark.parametrize("path", ["/ws/overlay/{sid}", "/overlay/ws/{sid}", "/ws/spectator/{sid}"])
def test_overlay_and_spectator_sockets_need_session_observe(gateway, table, path) -> None:
    _, session_id = table
    target = path.format(sid=session_id)

    assert _refused_code(gateway, target, "stranger_eve") == FORBIDDEN

    with gateway.websocket_connect(target, subprotocols=ws_subprotocols("spectator_sol")) as ws:
        assert ws.receive_json()["type"] == "overlay_connected"


def test_spectator_cannot_inject_an_overlay_roll_but_a_player_can(gateway, table) -> None:
    _, session_id = table
    path = f"/ws/overlay/{session_id}"
    roll = {"type": "dice_rolled", "roller_name": "Fake", "dice_formula": "1d20", "result": 20}

    with (
        gateway.websocket_connect(path, subprotocols=ws_subprotocols("spectator_sol")) as watcher,
        gateway.websocket_connect(path, subprotocols=ws_subprotocols("player_pip")) as player,
    ):
        assert watcher.receive_json()["type"] == "overlay_connected"
        assert player.receive_json()["type"] == "overlay_connected"

        watcher.send_json(roll)
        assert watcher.receive_json()["code"] == "PERMISSION_DENIED"
        assert _frame_within(player, SILENCE_SECONDS) is None

        player.send_json(roll)
        assert watcher.receive_json()["type"] == "roll_animation"


def test_player_cannot_dispatch_dm_whisper_or_turn_alert(gateway, table) -> None:
    _, session_id = table
    base = f"/api/v1/mobile/companion/{session_id}"
    whisper = {"recipient_id": "player_pip", "content": "psst"}
    alert = {"recipient_id": "player_pip", "character_name": "Pip"}

    for route, body in (("whisper", whisper), ("turn-alert", alert)):
        assert gateway.post(f"{base}/{route}", json=body).status_code == 401
        denied = gateway.post(f"{base}/{route}", json=body, headers=bearer("player_pip"))
        assert denied.status_code == 403
        allowed = gateway.post(f"{base}/{route}", json=body, headers=bearer("dm_dora"))
        assert allowed.status_code == 200, allowed.text


def test_speak_and_act_needs_session_participate(gateway, table) -> None:
    campaign_id, session_id = table
    body = {
        "speaker_id": "player_pip",
        "speaker_name": "Pip",
        "transcript": "I advance",
        "session_id": session_id,
        "campaign_id": campaign_id,
    }
    url = "/api/v1/watcher/speak-and-act"

    assert gateway.post(url, json=body, headers=bearer("spectator_sol")).status_code == 403
    assert gateway.post(url, json=body, headers=bearer("stranger_eve")).status_code == 403
    assert gateway.post(url, json=body, headers=bearer("player_pip")).status_code == 200


def test_campaign_socket_rejects_an_action_name_the_server_does_not_define(gateway, table) -> None:
    campaign_id, _ = table
    path = f"/ws/campaigns/{campaign_id}"

    with gateway.websocket_connect(path, subprotocols=ws_subprotocols("dm_dora")) as ws:
        assert ws.receive_json()["type"] == "connected"
        ws.send_json({"action": "manage", "note": "client-chosen permission name"})
        error = ws.receive_json()

    assert error["type"] == "error"
    assert error["code"] == "UNKNOWN_ACTION"
