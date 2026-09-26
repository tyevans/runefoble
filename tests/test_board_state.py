"""Tests for Board State microservice and spatial fog-of-war visibility."""

from uuid import uuid4

import pytest
from board_state.aggregate import BoardAggregate
from board_state.main import app as board_app
from httpx import ASGITransport, AsyncClient


@pytest.mark.asyncio
async def test_board_get_and_move():
    transport = ASGITransport(app=board_app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        # Get board
        res = await client.get("/api/v1/boards/session-test-1")
        assert res.status_code == 200
        data = res.json()
        assert data["session_id"] == "session-test-1"
        assert "t1" in data["tokens"]

        # Move token
        move_res = await client.post(
            "/api/v1/boards/session-test-1/move",
            json={"token_id": "t1", "to_x": 4, "to_y": 5},
        )
        assert move_res.status_code == 200
        moved = move_res.json()
        assert moved["x"] == 4
        assert moved["y"] == 5

        # Out-of-bounds move should fail
        oob_res = await client.post(
            "/api/v1/boards/session-test-1/move",
            json={"token_id": "t1", "to_x": 99, "to_y": 99},
        )
        assert oob_res.status_code == 400


@pytest.mark.asyncio
async def test_board_fog_of_war_eventsourcing():
    """Verify eventsource-py records FogOfWarRevealed when friendly tokens move."""
    board = BoardAggregate(uuid4())
    board.initialize_grid(cols=10, rows=10, session_id="test-fow-sess")

    # Place friendly token at (2, 2) with vision radius 2
    board.place_token(
        "p1", name="Valeros", token_type="pc", x=2, y=2, is_friendly=True, vision_radius=2
    )

    # Check revealed cells on board state
    revealed = board.state.revealed_cells
    # At (2,2) with radius 2 on 10x10, cells range from (0..4, 0..4) = 25 cells
    assert len(revealed) == 25
    assert [2, 2] in revealed
    assert [0, 0] in revealed
    assert [4, 4] in revealed


@pytest.mark.asyncio
async def test_board_visibility_api_filtering():
    """Verify visibility endpoint filters shrouded hostile tokens for players."""
    transport = ASGITransport(app=board_app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        # Player perspective (is_dm=False): hostile token t3 at (8, 8) is outside initial party vision at (2, 3)/(3, 3)
        vis_player = await client.get("/api/v1/boards/session-vis-test/visibility?is_dm=false")
        assert vis_player.status_code == 200
        data_player = vis_player.json()
        token_names_player = [t["name"] for t in data_player["tokens"]]
        assert "Valeros" in token_names_player
        assert "Kyra" in token_names_player
        assert "Goblin Scout" not in token_names_player

        # DM perspective (is_dm=true): all tokens including Goblin Scout are visible
        vis_dm = await client.get("/api/v1/boards/session-vis-test/visibility?is_dm=true")
        assert vis_dm.status_code == 200
        data_dm = vis_dm.json()
        token_names_dm = [t["name"] for t in data_dm["tokens"]]
        assert "Goblin Scout" in token_names_dm
