"""Blackbox tests for Board State Radial Menu Glyphs and Styles Decomposition.

TASK-0201: Board State Radial Menu Glyphs and Styles Modular Decomposition
Governed by:
- ADR-0004: Frontend Visualizer & Lit Component Architecture
- ADR-0012: Theming Tokens & Bauhaus Design System
- ADR-0013: Microfrontend Bounded Context Architecture
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
async def test_frontdoor_radial_actions_execution() -> None:
    """Verify all 5 radial menu actions execute successfully via public frontdoor HTTP routes."""
    transport = ASGITransport(app=board_app)
    session_id = f"radial-sess-{uuid4().hex[:8]}"

    async with AsyncClient(
        transport=transport, base_url="http://test", headers=bearer("user-test")
    ) as client:
        # 1. Create board through the public POST frontdoor
        init_res = await client.post(
            "/api/v1/boards",
            json={"campaign_id": BOARD_CAMPAIGN, "session_id": session_id, "cols": 12, "rows": 12},
        )
        assert init_res.status_code == 200

        # 2. Place active combatant token
        token_id = f"hero-{uuid4().hex[:6]}"
        place_res = await client.post(
            f"/api/v1/boards/{session_id}/tokens",
            json={
                "token_id": token_id,
                "name": "Valeros",
                "x": 3,
                "y": 3,
                "color": "#e63946",
                "is_hostile": False,
                "is_ai_controlled": False,
            },
        )
        assert place_res.status_code == 200

        # 3. Test execution for all 5 radial actions
        actions = ["attack", "dash", "disengage", "dodge", "cast"]
        for act in actions:
            act_res = await client.post(
                f"/api/v1/boards/{session_id}/tokens/{token_id}/action",
                json={
                    "action": act,
                    "initiated_by": "player",
                    "details": {"source": "radial_dial"},
                },
            )
            assert act_res.status_code == 200, f"Action '{act}' failed with: {act_res.text}"
            act_data = act_res.json()
            assert act_data["token_id"] == token_id
            assert act_data["action"] == act
            assert act_data["status"] == "executed"
            assert f"Action '{act}' successfully executed" in act_data["message"]


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
