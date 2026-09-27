"""Blackbox test suite for West Marches communal stronghold and tavern board UI.

Part of TASK-0176 / PRD-0018 / US-0050 / US-0058.
Governed by:
- ADR-0001: SpiceDB Zanzibar Object-Level Authorization
- Hard Invariant 1: Object-level authorization runs through SpiceDB Zanzibar schema
- Hard Invariant 6: File length limit (< 500 lines, target < 120 lines)
- Hard Invariant 7: Blackbox TDD with Frontdoor Setup
"""

from __future__ import annotations

from uuid import uuid4

import pytest
from fastapi.testclient import TestClient
from runefoble_auth.spicedb import MockSpiceDBClient


@pytest.mark.asyncio
async def test_blackbox_communal_stronghold_upgrade_and_boons(
    client: TestClient,
    spicedb_client: MockSpiceDBClient,
) -> None:
    """Verify upgrading communal stronghold facility recalculates shared boons and defense buffers."""
    campaign_id = str(uuid4())
    player_id = "alchemist_bryan"

    await spicedb_client.write_relationship(
        resource_type="campaign",
        resource_id=campaign_id,
        relation="player",
        subject_type="user",
        subject_id=player_id,
    )

    # 1. Upgrade Alchemical Workshop from Lv 1 to Lv 2
    upgrade_payload = {
        "facility_id": "alchemical_workshop",
        "gold_spent": 100,
        "materials_spent": {"timber": 20, "glass": 5},
    }
    upgrade_resp = client.post(
        f"/api/v1/campaigns/{campaign_id}/west-marches/stronghold/upgrade",
        json=upgrade_payload,
        headers={"x-user-id": player_id},
    )
    assert upgrade_resp.status_code == 200
    res = upgrade_resp.json()
    assert res["status"] == "upgraded"
    assert res["facility_id"] == "alchemical_workshop"
    assert res["new_tier"] == 2
    assert "Enhanced Potion Yield (+1 Potion)" in res["active_boons"]

    # 2. Upgrade Watchtower from Lv 1 to Lv 2 and check defensive buffer
    watch_resp = client.post(
        f"/api/v1/campaigns/{campaign_id}/west-marches/stronghold/upgrade",
        json={"facility_id": "watchtower", "gold_spent": 150},
        headers={"x-user-id": player_id},
    )
    assert watch_resp.status_code == 200
    assert watch_resp.json()["new_tier"] == 2
    assert watch_resp.json()["defensive_buffer"] >= 25


@pytest.mark.asyncio
async def test_blackbox_tavern_notice_board(
    client: TestClient,
    spicedb_client: MockSpiceDBClient,
) -> None:
    """Verify posting and reading communal tavern notice board bounties and rumors."""
    campaign_id = str(uuid4())
    player_id = "ranger_laura"

    await spicedb_client.write_relationship(
        resource_type="campaign",
        resource_id=campaign_id,
        relation="player",
        subject_type="user",
        subject_id=player_id,
    )

    # 1. Post bounty notice
    notice_payload = {
        "author_name": "Ranger Laura",
        "title": "Bounty: Cull the Marsh Trolls",
        "content": "Four marsh trolls sighted harassing supply convoys east of the Old Bridge.",
        "notice_type": "bounty",
        "bounty_reward": 150,
    }
    post_resp = client.post(
        f"/api/v1/campaigns/{campaign_id}/west-marches/tavern-board/notices",
        json=notice_payload,
        headers={"x-user-id": player_id},
    )
    assert post_resp.status_code == 201
    notice = post_resp.json()["notice"]
    assert notice["title"] == "Bounty: Cull the Marsh Trolls"
    assert notice["bounty_reward"] == 150

    # 2. Retrieve overview and verify notice is listed
    overview = client.get(
        f"/api/v1/campaigns/{campaign_id}/west-marches",
        headers={"x-user-id": player_id},
    ).json()
    assert len(overview["tavern_board"]) == 1
    assert overview["tavern_board"][0]["author_name"] == "Ranger Laura"
