"""Overlay vitals equal the owner views, and the camera outlives a gateway instance (TASK-0599).

The gateway holds no session or camera state. These tests drive the public routes only:
the camera is focused on `board_state` through its public POST route, and the overlay is read
through the gateway. Each test builds a new gateway app instance to show that nothing was kept
in process memory.
"""

from __future__ import annotations

import httpx
import pytest
from fastapi.testclient import TestClient
from gateway_api.main import app as gateway_app

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


def test_overlay_vitals_equal_the_board_owner_projection(
    board_gateway: TestClient, table: tuple[str, str]
) -> None:
    session_id, board_url = table
    owner = httpx.get(f"{board_url}/api/v1/boards/{session_id}/spectator", headers=bearer(OBSERVER))
    assert owner.status_code == 200, owner.text

    overlay = board_gateway.get(
        f"/overlay/party-vitals/{session_id}?format=json", headers=bearer(OBSERVER)
    )
    assert overlay.status_code == 200, overlay.text
    vitals = overlay.json()

    assert vitals["party"] == owner.json()["party"]
    assert vitals["camera"] == owner.json()["camera"]


def test_camera_focus_is_read_through_a_new_gateway_instance(
    table: tuple[str, str],
) -> None:
    session_id, board_url = table
    focused = httpx.post(
        f"{board_url}/api/v1/boards/{session_id}/camera/turn-started",
        json={"token_id": "t1"},
        headers=bearer(OWNER),
    )
    assert focused.status_code == 200, focused.text

    with TestClient(gateway_app) as first:
        before = first.get(
            f"/overlay/party-vitals/{session_id}?format=json", headers=bearer(OBSERVER)
        )
    assert before.status_code == 200, before.text

    with TestClient(gateway_app) as second:
        after = second.get(
            f"/overlay/party-vitals/{session_id}?format=json", headers=bearer(OBSERVER)
        )

    assert after.status_code == 200, after.text
    camera = after.json()["camera"]
    assert camera["active_token_id"] == "t1"
    assert camera["reason"] == "turn_started"
    assert camera == before.json()["camera"]
