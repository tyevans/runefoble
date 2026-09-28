"""Blackbox frontdoor tests for merchant haggling bargain flow and manifest.

Part of TASK-0281 / TASK-0262 / PRD-0024 / US-0075.
Governed by ADR-0001, ADR-0002, ADR-0004, ADR-0006, and Hard Invariant 7.
"""

from __future__ import annotations

from uuid import uuid4

import pytest
from fastapi.testclient import TestClient
from game_session.dependencies import STREAM_TAVERN
from runefoble_auth.spicedb import MockSpiceDBClient
from runefoble_platform.mock_redis import MockAsyncRedis

from .conftest import REPO_ROOT, create_test_establishment


def test_blackbox_merchant_haggling_manifest_and_components(client: TestClient) -> None:
    """Verify UI manifest advertises merchant-haggler and files exist per DoD."""
    res = client.get("/ui/manifest")
    assert res.status_code == 200
    manifest = res.json()
    assert "runefoble-merchant-haggler" in manifest["components"]
    assert "runefoble-dm-negotiation-drawer" in manifest["components"]

    haggler_file = REPO_ROOT / "frontend/src/components/minigames/runefoble-merchant-haggler.ts"
    dm_drawer_file = (
        REPO_ROOT / "frontend/src/components/dm-controls/runefoble-dm-negotiation-drawer.ts"
    )
    haggler_stories = REPO_ROOT / "frontend/src/stories/runefoble-merchant-haggler.stories.ts"
    dm_drawer_stories = (
        REPO_ROOT / "frontend/src/stories/runefoble-dm-negotiation-drawer.stories.ts"
    )

    for path in (haggler_file, dm_drawer_file, haggler_stories, dm_drawer_stories):
        assert path.is_file(), f"{path.name} must exist"

    assert len(haggler_file.read_text(encoding="utf-8").splitlines()) < 400
    assert len(dm_drawer_file.read_text(encoding="utf-8").splitlines()) < 400


@pytest.mark.asyncio
async def test_blackbox_establishment_haggle_gambits_flow(
    client: TestClient, spicedb: MockSpiceDBClient, mock_bus: MockAsyncRedis
) -> None:
    """US-0075 Scenario 1: Nicole negotiates for blade at Ember Anvil using Bulk Order Promise."""
    campaign_id = str(uuid4())
    dm_user_id = f"dm_{uuid4().hex[:8]}"
    player_user_id = f"player_{uuid4().hex[:8]}"

    await spicedb.write_relationship("campaign", campaign_id, "dungeon_master", "user", dm_user_id)
    await spicedb.write_relationship("campaign", campaign_id, "player", "user", player_user_id)

    # 1. Found settlement & construct establishment
    establishment_id = create_test_establishment(client, campaign_id, dm_user_id)

    # 2. Start bartering session with Bulk Order Promise gambit via frontdoor
    haggle_req = {
        "character_id": "char_nicole",
        "item_id": "blade_folded_adamantine",
        "item_name": "Folded Adamantine Blade",
        "base_price": 350,
        "initial_offer_gp": 260,
        "gambit": "bulk_order_promise",
        "roll_value": 18,
        "charisma_modifier": 3,
        "session_id": str(uuid4()),
        "campaign_id": campaign_id,
        "temperament": "Greedy",
    }
    haggle_res = client.post(
        f"/api/v1/establishments/{establishment_id}/haggle",
        json=haggle_req,
        headers={"x-user-id": player_user_id},
    )
    assert haggle_res.status_code == 200, haggle_res.text
    session_data = haggle_res.json()
    negotiation_id = session_data["negotiation_id"]

    assert session_data["status"] == "active"
    assert session_data["current_offer"] == 260
    assert session_data["counter_price"] < 350
    assert session_data["patience"] >= 5
    assert len(session_data["gambits_history"]) == 1

    entries = mock_bus.streams.get(STREAM_TAVERN, [])
    assert any(
        "gambit_executed" in str(e[1]).lower() or "gambit" in str(e[1]).lower() for e in entries
    )

    # 3. Execute second gambit: "Flattery / Praise"
    flattery_res = client.post(
        f"/api/v1/haggling/{negotiation_id}/gambit",
        json={
            "character_id": "char_nicole",
            "gambit": "flattery",
            "roll_value": 17,
            "charisma_modifier": 3,
        },
        headers={"x-user-id": player_user_id},
    )
    assert flattery_res.status_code == 200
    flattery_data = flattery_res.json()
    assert flattery_data["counter_price"] <= session_data["counter_price"]
    assert len(flattery_data["gambits_history"]) == 2
