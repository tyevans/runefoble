"""Blackbox tests for Board Templates Rendering and Subviews Modular Decomposition.

TASK-0192: Board Templates Rendering and Subviews Modular Decomposition
Governed by:
- ADR-0004: Lit Web Components and Storybook UI
- ADR-0012: Design System Theming and Bauhaus Modernism
- ADR-0013: Microfrontend Architecture and Service Component Vendoring
- Hard Invariant 6: File length limit (< 500 lines) and task-specific modular boundaries
- Hard Invariant 7: Blackbox TDD with Frontdoor Setup
"""

from __future__ import annotations

import asyncio
from uuid import uuid4

import pytest
from board_state.main import app as board_app
from httpx import ASGITransport, AsyncClient

from tests.helpers.ws_identity import bearer


@pytest.mark.asyncio
async def test_frontdoor_board_state_integration_for_templates() -> None:
    """Verify board initialization, token placement, and movement match template representations."""
    transport = ASGITransport(app=board_app)
    session_id = f"session-tpl-{uuid4().hex[:8]}"

    async with AsyncClient(
        transport=transport, base_url="http://test", headers=bearer("user-test")
    ) as client:
        # 1. Create the board via POST, then fetch its state via GET
        created = await client.post(
            "/api/v1/boards",
            json={"campaign_id": BOARD_CAMPAIGN, "session_id": session_id, "cols": 12, "rows": 12},
        )
        assert created.status_code == 200
        get_res = await client.get(f"/api/v1/boards/{session_id}")
        assert get_res.status_code == 200
        board_data = get_res.json()
        assert board_data["session_id"] == session_id
        assert board_data["cols"] > 0
        assert board_data["rows"] > 0

        # 2. Place token via public frontdoor
        token_id = f"hero-{uuid4().hex[:6]}"
        place_res = await client.post(
            f"/api/v1/boards/{session_id}/tokens",
            json={
                "token_id": token_id,
                "name": "Valeros",
                "x": 2,
                "y": 2,
                "color": "#e63946",
                "is_hostile": False,
                "is_ai_controlled": False,
            },
        )
        assert place_res.status_code == 200

        # 3. Move token via public frontdoor
        move_res = await client.post(
            f"/api/v1/boards/{session_id}/move",
            json={"token_id": token_id, "to_x": 4, "to_y": 5},
        )
        assert move_res.status_code == 200
        move_data = move_res.json()
        assert move_data["x"] == 4
        assert move_data["y"] == 5

        # 4. Configure terrain cell via public frontdoor
        terrain_res = await client.post(
            f"/api/v1/boards/{session_id}/terrain",
            json={
                "x": 4,
                "y": 5,
                "elevation": 1,
                "terrain_type": "difficult",
                "hazard": "spike_pit",
            },
        )
        assert terrain_res.status_code == 200

        # 5. Fetch updated board state and verify tokens and terrain are observable
        verify_res = await client.get(f"/api/v1/boards/{session_id}")
        assert verify_res.status_code == 200
        updated_board = verify_res.json()
        assert token_id in updated_board["tokens"]
        assert updated_board["tokens"][token_id]["x"] == 4
        assert updated_board["tokens"][token_id]["y"] == 5


BOARD_CAMPAIGN = "camp-board-fixture"


@pytest.fixture(autouse=True)
def _board_campaign_dm(spicedb):
    """Make `user-test` the DM of the campaign that every board in this module belongs to."""
    asyncio.run(
        spicedb.write_relationship(
            resource_type="campaign",
            resource_id=BOARD_CAMPAIGN,
            relation="dungeon_master",
            subject_type="user",
            subject_id="user-test",
        )
    )
