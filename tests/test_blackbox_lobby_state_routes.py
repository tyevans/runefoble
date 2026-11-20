"""Blackbox frontdoor tests: lobby readiness and the AI stand-in are kept by the owner (TASK-0952).

The lobby state lives in game_session. The gateway proxies the readiness, seat stand-in and
lobby-character routes and stores nothing. After the owner saves a change, the gateway tells
every session socket with `player_readiness` or `player_stand_in`. A reload reads the stored
state from `GET /api/v1/sessions/{id}`.

Stand-in rule: a player sets the stand-in of their own seat. A caller with `session.control`
(the DM, `campaign#run_session`) sets the stand-in of any seat. Any other caller gets 403.
Governed by ADR-0001, ADR-0015 (a), (b), (c), ADR-0014 and Hard Invariant 7. Setup and
assertions use public gateway routes only.
"""

from __future__ import annotations

from collections.abc import Iterator
from concurrent.futures import ThreadPoolExecutor
from concurrent.futures import TimeoutError as FutureTimeout
from typing import Any

import pytest
from fastapi.testclient import TestClient
from starlette.testclient import WebSocketTestSession

from tests.helpers.ws_identity import bearer, ws_subprotocols
from tests.realtime_session import open_table

pytestmark = pytest.mark.usefixtures("trusted_ws_issuer")

DM = "dm_evelyn"
PLAYER = "player_valeros"
OTHER = "player_sarah"
SILENCE_SECONDS = 1.0


def _seat(gateway: TestClient, campaign_id: str, session_id: str, user: str, name: str) -> str:
    """Create a character for `user`, seat it in the lobby, and select it. Return the character id."""
    created = gateway.post(
        "/api/v1/characters",
        json={"name": name, "character_class": "Fighter", "max_hp": 24, "campaign_id": campaign_id},
        headers=bearer(user),
    )
    assert created.status_code == 201, created.text
    character_id = created.json()["id"]
    seated = gateway.post(
        f"/api/v1/sessions/{session_id}/join",
        json={"character_id": character_id, "character_name": name, "character_class": "Fighter"},
        headers=bearer(user),
    )
    assert seated.status_code == 200, seated.text
    picked = gateway.post(
        f"/api/v1/sessions/{session_id}/lobby/character",
        json={"character_id": character_id},
        headers=bearer(user),
    )
    assert picked.status_code == 200, picked.text
    return character_id


@pytest.fixture
def lobby(gateway: TestClient, game_session_upstream: str) -> Iterator[tuple[str, str]]:
    """A lobby with two players, each seated with a character. Returns (campaign id, session id)."""
    campaign_id, session_id = open_table(
        gateway, game_session_upstream, DM, {PLAYER: "player", OTHER: "player"}
    )
    _seat(gateway, campaign_id, session_id, PLAYER, "Valeros")
    _seat(gateway, campaign_id, session_id, OTHER, "Sarah")
    yield campaign_id, session_id


def _frame_within(ws: WebSocketTestSession, seconds: float) -> dict[str, Any] | None:
    """Return the next frame, or None when no frame arrives within `seconds`."""
    pool = ThreadPoolExecutor(max_workers=1)
    pending = pool.submit(ws.receive_json)
    try:
        return pending.result(timeout=seconds)
    except FutureTimeout:
        return None
    finally:
        pool.shutdown(wait=False)


def _stand_in(gateway: TestClient, session_id: str, seat: str, caller: str, is_absent: bool):
    return gateway.post(
        f"/api/v1/sessions/{session_id}/seats/{seat}/stand-in",
        json={"is_absent": is_absent},
        headers=bearer(caller),
    )


def _participant(gateway: TestClient, session_id: str, seat: str) -> dict[str, Any]:
    read = gateway.get(f"/api/v1/sessions/{session_id}", headers=bearer(DM))
    assert read.status_code == 200, read.text
    return read.json()["participants"][seat]


def test_readiness_is_saved_by_the_owner_and_reaches_every_socket(gateway, lobby) -> None:
    _, session_id = lobby
    path = f"/ws/session/{session_id}"

    with (
        gateway.websocket_connect(path, subprotocols=ws_subprotocols(PLAYER)) as player,
        gateway.websocket_connect(path, subprotocols=ws_subprotocols(DM)) as dm,
    ):
        assert player.receive_json()["type"] == "connected"
        assert dm.receive_json()["type"] == "connected"

        saved = gateway.post(
            f"/api/v1/sessions/{session_id}/lobby/readiness",
            json={"is_ready": True},
            headers=bearer(PLAYER),
        )

        assert saved.status_code == 200, saved.text
        assert saved.json()["lobby_readiness"][PLAYER] is True
        expected = {"type": "player_readiness", "userId": PLAYER, "isReady": True}
        assert dm.receive_json() == expected
        assert player.receive_json() == expected

    read = gateway.get(f"/api/v1/sessions/{session_id}", headers=bearer(PLAYER))
    assert read.json()["lobby_readiness"][PLAYER] is True


def test_readiness_without_a_token_is_refused_and_nothing_is_saved(gateway, lobby) -> None:
    _, session_id = lobby

    refused = gateway.post(
        f"/api/v1/sessions/{session_id}/lobby/readiness", json={"is_ready": True}
    )

    assert refused.status_code == 401
    read = gateway.get(f"/api/v1/sessions/{session_id}", headers=bearer(PLAYER))
    assert PLAYER not in read.json()["lobby_readiness"]


def test_player_sets_own_stand_in_and_every_socket_gets_the_frame(gateway, lobby) -> None:
    _, session_id = lobby
    path = f"/ws/session/{session_id}"

    with (
        gateway.websocket_connect(path, subprotocols=ws_subprotocols(PLAYER)) as player,
        gateway.websocket_connect(path, subprotocols=ws_subprotocols(DM)) as dm,
    ):
        assert player.receive_json()["type"] == "connected"
        assert dm.receive_json()["type"] == "connected"

        left = _stand_in(gateway, session_id, PLAYER, PLAYER, True)

        assert left.status_code == 200, left.text
        expected = {"type": "player_stand_in", "userId": PLAYER, "isAbsent": True}
        assert dm.receive_json() == expected
        assert player.receive_json() == expected

    stored = _participant(gateway, session_id, PLAYER)
    assert stored["is_present"] is False
    assert stored["is_stand_in_active"] is True


def test_player_cannot_set_another_seats_stand_in(gateway, lobby) -> None:
    _, session_id = lobby
    path = f"/ws/session/{session_id}"

    with (
        gateway.websocket_connect(path, subprotocols=ws_subprotocols(OTHER)) as other,
        gateway.websocket_connect(path, subprotocols=ws_subprotocols(DM)) as dm,
    ):
        assert other.receive_json()["type"] == "connected"
        assert dm.receive_json()["type"] == "connected"

        refused = _stand_in(gateway, session_id, PLAYER, OTHER, True)

        assert refused.status_code == 403, refused.text
        assert _frame_within(dm, SILENCE_SECONDS) is None

    stored = _participant(gateway, session_id, PLAYER)
    assert stored["is_present"] is True
    assert stored["is_stand_in_active"] is False


def test_dm_sets_another_seats_stand_in_and_the_state_survives_a_reload(gateway, lobby) -> None:
    _, session_id = lobby
    path = f"/ws/session/{session_id}"

    with (
        gateway.websocket_connect(path, subprotocols=ws_subprotocols(PLAYER)) as player,
        gateway.websocket_connect(path, subprotocols=ws_subprotocols(DM)) as dm,
    ):
        assert player.receive_json()["type"] == "connected"
        assert dm.receive_json()["type"] == "connected"

        set_by_dm = _stand_in(gateway, session_id, OTHER, DM, True)

        assert set_by_dm.status_code == 200, set_by_dm.text
        expected = {"type": "player_stand_in", "userId": OTHER, "isAbsent": True}
        assert dm.receive_json() == expected
        assert player.receive_json() == expected

    # A reload reads the stored state from the owner, not from the page.
    stored = _participant(gateway, session_id, OTHER)
    assert stored["is_present"] is False
    assert stored["is_stand_in_active"] is True

    sheet = gateway.get(f"/api/v1/characters/{stored['character_id']}", headers=bearer(OTHER))
    assert sheet.status_code == 200, sheet.text
    assert sheet.json()["isAiStandIn"] is True


def test_dm_releases_another_seats_stand_in(gateway, lobby) -> None:
    _, session_id = lobby
    assert _stand_in(gateway, session_id, OTHER, DM, True).status_code == 200

    released = _stand_in(gateway, session_id, OTHER, DM, False)

    assert released.status_code == 200, released.text
    stored = _participant(gateway, session_id, OTHER)
    assert stored["is_present"] is True
    assert stored["is_stand_in_active"] is False
    sheet = gateway.get(f"/api/v1/characters/{stored['character_id']}", headers=bearer(OTHER))
    assert sheet.json()["isAiStandIn"] is False


def test_stand_in_without_a_token_is_refused(gateway, lobby) -> None:
    _, session_id = lobby

    refused = gateway.post(
        f"/api/v1/sessions/{session_id}/seats/{PLAYER}/stand-in", json={"is_absent": True}
    )

    assert refused.status_code == 401
    assert _participant(gateway, session_id, PLAYER)["is_present"] is True


def test_a_client_frame_of_a_lobby_change_is_unknown_and_not_relayed(gateway, lobby) -> None:
    _, session_id = lobby
    path = f"/ws/session/{session_id}"

    with (
        gateway.websocket_connect(path, subprotocols=ws_subprotocols(PLAYER)) as player,
        gateway.websocket_connect(path, subprotocols=ws_subprotocols(DM)) as dm,
    ):
        assert player.receive_json()["type"] == "connected"
        assert dm.receive_json()["type"] == "connected"

        player.send_json({"type": "player_stand_in", "userId": PLAYER, "isAbsent": True})
        error = player.receive_json()

        assert (error["type"], error["code"]) == ("error", "UNKNOWN_FRAME")
        assert _frame_within(dm, SILENCE_SECONDS) is None
