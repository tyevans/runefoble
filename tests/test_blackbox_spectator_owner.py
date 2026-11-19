"""Owner-side spectator projection and camera blackbox tests (TASK-0823).

The redaction runs in the owning services. `board_state` serves the board projection and the
camera. `game_session` serves the session projection. The tests call both owners over their
public HTTP routes, the same way the gateway does.
"""

from __future__ import annotations

import httpx
import pytest
from fastapi.testclient import TestClient

from tests.helpers.spectator_table import open_board_table
from tests.helpers.ws_identity import bearer

pytestmark = pytest.mark.usefixtures("trusted_ws_issuer")

OBSERVER = "spectator_sol"
OWNER = "dm_dora"


@pytest.fixture
def table(
    board_gateway: TestClient, game_session_upstream: str, board_state_upstream: str
) -> tuple[str, str]:
    """A live session with a board: one party token and one monster."""
    _, session_id = open_board_table(
        board_gateway,
        game_session_upstream,
        board_state_upstream,
        OWNER,
        {OBSERVER: "spectator"},
        start=True,
    )
    return session_id, board_state_upstream


def test_board_owner_spectator_view_omits_monsters(table: tuple[str, str]) -> None:
    session_id, board_url = table
    res = httpx.get(f"{board_url}/api/v1/boards/{session_id}/spectator", headers=bearer(OBSERVER))

    assert res.status_code == 200, res.text
    body = res.json()
    assert body["cols"] == 8
    assert body["rows"] == 8
    assert [tok["name"] for tok in body["tokens"]] == ["Valeros"]
    assert [member["name"] for member in body["party"]] == ["Valeros"]
    assert body["party"][0]["hp"] == 45
    assert "Goblin Stalker" not in res.text
    assert body["tokens"][0]["token_type"] == "pc"


def test_board_owner_spectator_view_refuses_a_stranger(table: tuple[str, str]) -> None:
    session_id, board_url = table
    res = httpx.get(
        f"{board_url}/api/v1/boards/{session_id}/spectator", headers=bearer("stranger_eve")
    )
    assert res.status_code == 403


def test_session_owner_spectator_view_projects_public_state(
    board_gateway: TestClient, table: tuple[str, str], game_session_upstream: str
) -> None:
    session_id, _ = table
    res = httpx.get(
        f"{game_session_upstream}/api/v1/sessions/{session_id}/spectator",
        headers=bearer(OBSERVER),
    )

    assert res.status_code == 200, res.text
    body = res.json()
    assert body["session_id"] == session_id
    assert body["status"] == "active"
    assert body["round"] == 1
    assert isinstance(body["chronicle"], list)
    assert "dm_notes" not in res.text


def test_session_owner_spectator_view_is_404_for_an_unknown_session(
    game_session_upstream: str,
) -> None:
    unknown = "00000000-0000-4000-8000-000000000999"
    res = httpx.get(
        f"{game_session_upstream}/api/v1/sessions/{unknown}/spectator", headers=bearer(OBSERVER)
    )
    assert res.status_code == 404


def test_session_owner_spectator_view_refuses_a_stranger(
    table: tuple[str, str], game_session_upstream: str
) -> None:
    session_id, _ = table
    res = httpx.get(
        f"{game_session_upstream}/api/v1/sessions/{session_id}/spectator",
        headers=bearer("stranger_eve"),
    )
    assert res.status_code == 403


def test_camera_turn_started_is_stored_by_the_board_owner(table: tuple[str, str]) -> None:
    session_id, board_url = table
    posted = httpx.post(
        f"{board_url}/api/v1/boards/{session_id}/camera/turn-started",
        json={"token_id": "t1", "character_id": "c-valeros"},
        headers=bearer(OWNER),
    )
    assert posted.status_code == 200, posted.text
    camera = posted.json()
    assert camera["target_x"] == 2.0
    assert camera["target_y"] == 3.0
    assert camera["reason"] == "turn_started"
    assert camera["duration_ms"] == 300

    read = httpx.get(f"{board_url}/api/v1/boards/{session_id}/camera", headers=bearer(OBSERVER))
    assert read.status_code == 200, read.text
    assert read.json()["target_x"] == 2.0
    assert read.json()["active_token_id"] == "t1"


def test_camera_token_moved_centers_on_the_destination(table: tuple[str, str]) -> None:
    session_id, board_url = table
    posted = httpx.post(
        f"{board_url}/api/v1/boards/{session_id}/camera/token-moved",
        json={"token_id": "t1", "to_x": 4, "to_y": 4},
        headers=bearer(OWNER),
    )
    assert posted.status_code == 200, posted.text
    assert posted.json()["target_x"] == 4.0
    assert posted.json()["target_y"] == 4.0
    assert posted.json()["reason"] == "token_moved"


def test_camera_refuses_a_token_that_is_not_on_the_board(table: tuple[str, str]) -> None:
    session_id, board_url = table
    posted = httpx.post(
        f"{board_url}/api/v1/boards/{session_id}/camera/turn-started",
        json={"token_id": "no-such-token"},
        headers=bearer(OWNER),
    )
    assert posted.status_code == 409


def test_camera_refuses_a_spectator(table: tuple[str, str]) -> None:
    session_id, board_url = table
    posted = httpx.post(
        f"{board_url}/api/v1/boards/{session_id}/camera/token-moved",
        json={"token_id": "t1", "to_x": 4, "to_y": 4},
        headers=bearer(OBSERVER),
    )
    assert posted.status_code == 403


def test_camera_before_any_focus_reads_the_default(table: tuple[str, str]) -> None:
    session_id, board_url = table
    read = httpx.get(f"{board_url}/api/v1/boards/{session_id}/camera", headers=bearer(OBSERVER))
    assert read.status_code == 200, read.text
    assert read.json()["reason"] == "init"
    assert read.json()["zoom"] == 1.0


def test_session_owner_spectator_view_carries_the_dm_atmosphere(
    table: tuple[str, str], game_session_upstream: str
) -> None:
    session_id, _ = table
    posted = httpx.post(
        f"{game_session_upstream}/api/v1/sessions/{session_id}/atmosphere",
        json={
            "location_name": "Forgotten Sepulcher",
            "lighting": "Pale eerie luminescence",
            "mood": "Ominous",
            "description": "Granite walls sweat ancient moisture.",
            "ambient_audio_prompt": "dripping water",
        },
        headers=bearer(OWNER),
    )
    assert posted.status_code == 200, posted.text

    res = httpx.get(
        f"{game_session_upstream}/api/v1/sessions/{session_id}/spectator",
        headers=bearer(OBSERVER),
    )
    assert res.status_code == 200, res.text
    assert res.json()["atmosphere"]["location_name"] == "Forgotten Sepulcher"
    assert res.json()["atmosphere"]["mood"] == "Ominous"
