"""Frontdoor setup for spectator and overlay tests: a campaign, a live session, and a board (TASK-0809).

The gateway reads the session and the board from the owning services. A test therefore runs
`game_session` and `board_state` as live loopback upstreams. Every row is written through a
public route: the campaign and session by `open_table`, the board and its tokens by the
`board_state` routes, and the session start by the `game_session` route. No test seeds a store.
"""

from __future__ import annotations

from collections.abc import Callable, Iterator

import httpx
import pytest
from fastapi.testclient import TestClient
from gateway_api.main import app as gateway_app

from tests.helpers.ws_identity import bearer
from tests.realtime_session import open_table

PARTY_TOKEN = {
    "token_id": "t1",
    "name": "Valeros",
    "token_type": "pc",
    "x": 2,
    "y": 3,
    "hp": 45,
}
MONSTER_TOKEN = {
    "token_id": "t_goblin",
    "name": "Goblin Stalker",
    "token_type": "monster",
    "x": 6,
    "y": 2,
    "hp": 12,
}


@pytest.fixture
def board_gateway(
    game_session_upstream: str,
    board_state_upstream: str,
    character_sheet_upstream: str,
    voice_agent_upstream: str,
) -> Iterator[TestClient]:
    """A gateway client wired to live game_session and board_state upstreams."""
    with TestClient(gateway_app) as client:
        yield client


def open_board_table(
    gateway: TestClient,
    session_url: str,
    board_url: str,
    owner: str,
    members: dict[str, str] | None = None,
    *,
    start: bool = False,
) -> tuple[str, str]:
    """Return (campaign_id, session_id) with a board that holds a player token and a monster.

    `start` moves the session from the lobby to active through `game_session`.
    """
    campaign_id, session_id = open_table(gateway, session_url, owner, members)
    created = httpx.post(
        f"{board_url}/api/v1/boards",
        json={"campaign_id": campaign_id, "session_id": session_id, "cols": 8, "rows": 8},
        headers=bearer(owner),
    )
    assert created.status_code == 200, created.text
    for token in (PARTY_TOKEN, MONSTER_TOKEN):
        placed = httpx.post(
            f"{board_url}/api/v1/boards/{session_id}/tokens",
            json={**token, "is_friendly": token["token_type"] == "pc"},
            headers=bearer(owner),
        )
        assert placed.status_code == 200, placed.text
    if start:
        started = httpx.post(
            f"{session_url}/api/v1/sessions/{session_id}/start", headers=bearer(owner)
        )
        assert started.status_code == 200, started.text
    return campaign_id, session_id


@pytest.fixture
def board_table(
    board_gateway: TestClient, game_session_upstream: str, board_state_upstream: str
) -> Callable[..., tuple[str, str]]:
    """Return `board_table(owner, members, start=...)`, which yields (campaign_id, session_id)."""

    def _open(
        owner: str, members: dict[str, str] | None = None, *, start: bool = False
    ) -> tuple[str, str]:
        return open_board_table(
            board_gateway,
            game_session_upstream,
            board_state_upstream,
            owner,
            members,
            start=start,
        )

    return _open
