"""Blackbox frontdoor tests for Game Master arbitration, mood nudges, and Zanzibar permissions.

Part of TASK-0281 / TASK-0262 / PRD-0024 / US-0075.
Governed by ADR-0001, ADR-0002, ADR-0006, and Hard Invariant 7.
"""

from __future__ import annotations

from uuid import uuid4

import pytest
from fastapi.testclient import TestClient
from game_session.dependencies import STREAM_TAVERN
from runefoble_auth.spicedb import MockSpiceDBClient
from runefoble_platform.mock_redis import MockAsyncRedis


@pytest.mark.asyncio
async def test_blackbox_dm_arbitration_controls_and_override(
    client: TestClient, spicedb: MockSpiceDBClient, mock_bus: MockAsyncRedis
) -> None:
    """US-0075 Scenario 2: DM intervenes in real time, alters mood, and forces acceptance."""
    campaign_id = str(uuid4())
    dm_user_id = f"dm_{uuid4().hex[:8]}"
    player_id = f"player_{uuid4().hex[:8]}"

    await spicedb.write_relationship("campaign", campaign_id, "dungeon_master", "user", dm_user_id)
    await spicedb.write_relationship("campaign", campaign_id, "player", "user", player_id)

    # 1. Start negotiation
    start_res = client.post(
        "/api/v1/haggling/start",
        json={
            "character_id": "char_nicole",
            "item_id": "potion_invisibility",
            "base_price": 200,
            "initial_offer_gp": 140,
            "campaign_id": campaign_id,
        },
        headers={"x-user-id": player_id},
    )
    assert start_res.status_code == 200
    neg_id = start_res.json()["negotiation_id"]

    # 2. DM nudges mood with "soothe_merchant"
    soothe_bark = "The merchant takes a calming breath."
    soothe_res = client.patch(
        f"/api/v1/haggling/{neg_id}/dm-override",
        json={"action": "soothe_merchant", "narrative_bark": soothe_bark},
        headers={"x-user-id": dm_user_id},
    )
    assert soothe_res.status_code == 200
    assert soothe_res.json()["merchant_mood_score"] > 0
    assert soothe_res.json()["last_bark"] == soothe_bark

    # 3. DM forces deal acceptance at 150 gold with custom narrative bark
    bark = "Torvin scowls, then nods in begrudging respect. Done."
    dm_accept_res = client.patch(
        f"/api/v1/haggling/{neg_id}/dm-override",
        json={"action": "force_accept", "override_price_gp": 150, "narrative_bark": bark},
        headers={"x-user-id": dm_user_id},
    )
    assert dm_accept_res.status_code == 200
    closed_data = dm_accept_res.json()
    assert closed_data["status"] == "completed"
    assert closed_data["counter_price"] == 150
    assert closed_data["last_bark"] == bark

    # 4. Verify domain events emitted to Redis streams: NegotiationConcluded and CurrencyDeducted
    entries = mock_bus.streams.get(STREAM_TAVERN, [])
    assert any("negotiation_concluded" in str(entry[1]).lower() for entry in entries)
    assert any("currency_deducted" in str(entry[1]).lower() for entry in entries)

    # 5. Subsequent attempts to override or gambit on a closed deal fail cleanly with zero race condition
    stale_gambit = client.post(
        f"/api/v1/haggling/{neg_id}/gambit",
        json={"character_id": "char_nicole", "gambit": "flattery", "roll_value": 15},
        headers={"x-user-id": player_id},
    )
    assert stale_gambit.status_code == 400


@pytest.mark.asyncio
async def test_blackbox_spicedb_zanzibar_arbitration_permission(
    client: TestClient, spicedb: MockSpiceDBClient
) -> None:
    """Verify unauthorized player cannot execute DM overrides (ADR-0001 Zanzibar enforcement)."""
    campaign_id = str(uuid4())
    player_id = f"player_{uuid4().hex[:8]}"
    stranger_id = f"stranger_{uuid4().hex[:8]}"

    await spicedb.write_relationship("campaign", campaign_id, "player", "user", player_id)

    start_res = client.post(
        "/api/v1/haggling/start",
        json={
            "character_id": "char_bram",
            "item_id": "helm_iron",
            "base_price": 50,
            "campaign_id": campaign_id,
        },
        headers={"x-user-id": player_id},
    )
    assert start_res.status_code == 200
    neg_id = start_res.json()["negotiation_id"]

    # Unauthorized player attempts DM override
    denied_res = client.patch(
        f"/api/v1/haggling/{neg_id}/dm-override",
        json={"action": "force_accept", "override_price_gp": 10},
        headers={"x-user-id": stranger_id},
    )
    assert denied_res.status_code == 403, "Stranger must be rejected by Zanzibar authorization"
