"""Blackbox tests and modular decomposition invariants for board_state.models."""

from __future__ import annotations

from uuid import uuid4

import pytest
from board_state.main import app as board_app
from httpx import ASGITransport, AsyncClient

from tests.helpers.campaign_setup import create_dm_campaign
from tests.helpers.ws_identity import bearer


def test_board_state_transitions_behavior():
    """Verify BoardState state transitions and mutation helpers execute accurately."""
    from board_state.models.board import BoardState
    from board_state.models.tokens import PlacedTokenState

    board = BoardState.initial(uuid4(), session_id="test-session-123", cols=10, rows=10)
    assert board.cols == 10
    assert board.rows == 10
    assert len(board.tokens) == 0

    # Place token
    hero = PlacedTokenState(token_id="hero-1", name="Valeros", x=1, y=1)
    board = board.with_token_placed(hero)
    assert "hero-1" in board.tokens

    # Move token
    board = board.with_token_moved("hero-1", to_x=3, to_y=4, active_hazard=None)
    assert board.tokens["hero-1"].x == 3
    assert board.tokens["hero-1"].y == 4

    # Fog reveal
    board = board.with_fog_revealed([[3, 4], [3, 5]])
    assert [3, 4] in board.revealed_cells
    assert [3, 5] in board.revealed_cells

    # Terrain modify
    board = board.with_terrain_modified(x=3, y=4, elevation=2, terrain_type="lava", hazard="fire")
    assert "fire" in board.active_hazards
    assert board.terrain_cells[(3, 4)].elevation == 2

    # Decals and decay
    board = board.with_area_effect([[3, 4]], decal_type="scorched_earth", decal_duration_rounds=2)
    assert len(board.active_decals) == 1
    board = board.with_decals_decayed(rounds=1)
    assert len(board.active_decals) == 1
    assert board.active_decals[0].rounds_remaining == 1
    board = board.with_decals_decayed(rounds=1)
    assert len(board.active_decals) == 0


@pytest.mark.asyncio
async def test_frontdoor_board_endpoints(board_campaign: str):
    """Verify frontdoor HTTP operations through public REST endpoints."""
    transport = ASGITransport(app=board_app)
    async with AsyncClient(
        transport=transport, base_url="http://test", headers=bearer("user-test")
    ) as client:
        created = await client.post(
            "/api/v1/boards",
            json={
                "campaign_id": board_campaign,
                "session_id": "session-test-modular",
                "cols": 12,
                "rows": 12,
            },
        )
        assert created.status_code == 200
        # Get board state
        res = await client.get("/api/v1/boards/session-test-modular")
        assert res.status_code == 200
        data = res.json()
        assert data["session_id"] == "session-test-modular"

        # Place token
        place_res = await client.post(
            "/api/v1/boards/session-test-modular/tokens",
            json={"token_id": "tok-mod-1", "name": "Rogue", "x": 2, "y": 2},
        )
        assert place_res.status_code == 200

        # Move token
        move_res = await client.post(
            "/api/v1/boards/session-test-modular/move",
            json={"token_id": "tok-mod-1", "to_x": 3, "to_y": 3},
        )
        assert move_res.status_code == 200
        moved = move_res.json()
        assert moved["x"] == 3
        assert moved["y"] == 3

        # Configure terrain
        terrain_res = await client.post(
            "/api/v1/boards/session-test-modular/terrain",
            json={"x": 3, "y": 3, "elevation": 1, "terrain_type": "stone", "hazard": None},
        )
        assert terrain_res.status_code == 200


@pytest.fixture(autouse=True)
def board_campaign(trusted_ws_issuer) -> str:
    """The campaign that every board in this module belongs to. `user-test` runs it."""
    return create_dm_campaign("user-test")
