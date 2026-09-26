import pytest
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
