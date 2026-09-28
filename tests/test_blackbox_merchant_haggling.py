"""Blackbox frontdoor tests for Interactive Merchant Haggling Engine and DM Controls.

Part of TASK-0262 / PRD-0024 / US-0075.
Governed by ADR-0001 (SpiceDB Zanzibar), ADR-0002 (Domain Events via eventsource-py),
ADR-0004 (Lit Web Components), ADR-0006 (Redis Streams), and Hard Invariant 7.
"""

from __future__ import annotations

from pathlib import Path
from uuid import uuid4

import pytest
from fastapi.testclient import TestClient
from game_session.dependencies import (
    STREAM_TAVERN,
    set_event_bus,
    set_spicedb_client,
)
from game_session.main import app
from runefoble_auth.spicedb import MockSpiceDBClient
from runefoble_platform.mock_redis import MockAsyncRedis
from runefoble_platform.redis_bus import RedisStreamsEventBus

REPO_ROOT = Path(__file__).resolve().parent.parent


@pytest.fixture
def mock_bus() -> MockAsyncRedis:
    bus_client = MockAsyncRedis()
    set_event_bus(RedisStreamsEventBus(client=bus_client))
    yield bus_client
    set_event_bus(None)


@pytest.fixture
def spicedb() -> MockSpiceDBClient:
    db = MockSpiceDBClient()
    set_spicedb_client(db)
    yield db
    set_spicedb_client(None)


@pytest.fixture
def client(spicedb: MockSpiceDBClient, mock_bus: MockAsyncRedis) -> TestClient:
    return TestClient(app)


def test_blackbox_merchant_haggling_manifest_and_components(client: TestClient) -> None:
    """Verify UI manifest advertises merchant-haggler and files exist per DoD."""
    res = client.get("/ui/manifest")
    assert res.status_code == 200
    manifest = res.json()
    assert "runefoble-merchant-haggler" in manifest["components"]
    assert "runefoble-dm-negotiation-drawer" in manifest["components"]

    # Verify component source files exist and adhere to line limit (<400 lines)
    haggler_file = (
        REPO_ROOT
        / "frontend"
        / "src"
        / "components"
        / "minigames"
        / "runefoble-merchant-haggler.ts"
    )
    dm_drawer_file = (
        REPO_ROOT
        / "frontend"
        / "src"
        / "components"
        / "dm-controls"
        / "runefoble-dm-negotiation-drawer.ts"
    )
    haggler_stories = (
        REPO_ROOT / "frontend" / "src" / "stories" / "runefoble-merchant-haggler.stories.ts"
    )
    dm_drawer_stories = (
        REPO_ROOT / "frontend" / "src" / "stories" / "runefoble-dm-negotiation-drawer.stories.ts"
    )

    assert haggler_file.is_file(), "Merchant haggler component must exist"
    assert dm_drawer_file.is_file(), "DM negotiation drawer must exist"
    assert haggler_stories.is_file(), "Merchant haggler stories must exist"
    assert dm_drawer_stories.is_file(), "DM drawer stories must exist"

    haggler_lines = len(haggler_file.read_text(encoding="utf-8").splitlines())
    dm_drawer_lines = len(dm_drawer_file.read_text(encoding="utf-8").splitlines())
    assert haggler_lines < 400, f"Haggler lines {haggler_lines} exceeds 400"
    assert dm_drawer_lines < 400, f"DM drawer lines {dm_drawer_lines} exceeds 400"


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
    settlement_res = client.post(
        f"/api/v1/campaigns/{campaign_id}/settlements",
        json={
            "name": "Oakhaven",
            "scale": "market_town",
            "biome": "river_valley",
            "districts": ["artisan"],
        },
        headers={"x-user-id": dm_user_id},
    )
    assert settlement_res.status_code == 201
    settlement_id = settlement_res.json()["settlement_id"]

    est_res = client.post(
        f"/api/v1/settlements/{settlement_id}/establishments",
        json={
            "district_id": "artisan",
            "category": "commerce",
            "name": "The Ember Anvil",
            "tier": 2,
            "operating_cost": 20,
        },
        headers={"x-user-id": dm_user_id},
    )
    assert est_res.status_code == 201
    establishment_id = est_res.json()["establishment_id"]

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

    # Verify GambitExecuted published to Redis stream
    entries = mock_bus.streams.get(STREAM_TAVERN, [])
    assert any(
        "gambit_executed" in str(entry[1]).lower() or "gambit" in str(entry[1]).lower()
        for entry in entries
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


@pytest.mark.asyncio
async def test_blackbox_patience_depletion_and_ejection(
    client: TestClient, spicedb: MockSpiceDBClient, mock_bus: MockAsyncRedis
) -> None:
    """Verify that failing aggressive intimidation depletes patience and terminates the interaction."""
    campaign_id = str(uuid4())
    player_id = f"player_{uuid4().hex[:8]}"
    await spicedb.write_relationship("campaign", campaign_id, "player", "user", player_id)

    # Start negotiation
    start_res = client.post(
        "/api/v1/haggling/start",
        json={
            "character_id": "char_krag",
            "item_id": "gem_ruby",
            "item_name": "Flawless Ruby",
            "base_price": 500,
            "initial_offer_gp": 200,
            "campaign_id": campaign_id,
            "temperament": "Stubborn",
        },
        headers={"x-user-id": player_id},
    )
    assert start_res.status_code == 200
    negotiation_id = start_res.json()["negotiation_id"]
    assert start_res.json()["patience"] == 5

    # 1. Fail intimidation roll twice (roll 2 vs DC 17 -> -2 patience each)
    res1 = client.post(
        f"/api/v1/haggling/{negotiation_id}/gambit",
        json={"character_id": "char_krag", "gambit": "hard_intimidation", "roll_value": 2},
        headers={"x-user-id": player_id},
    )
    assert res1.status_code == 200
    assert res1.json()["patience"] == 3
    assert res1.json()["status"] == "active"

    res2 = client.post(
        f"/api/v1/haggling/{negotiation_id}/gambit",
        json={"character_id": "char_krag", "gambit": "hard_intimidation", "roll_value": 3},
        headers={"x-user-id": player_id},
    )
    assert res2.status_code == 200
    assert res2.json()["patience"] == 1
    assert res2.json()["status"] == "active"

    # 2. Final failed gambit empties patience and kicks player out
    res3 = client.post(
        f"/api/v1/haggling/{negotiation_id}/gambit",
        json={"character_id": "char_krag", "gambit": "point_out_flaw", "roll_value": 4},
        headers={"x-user-id": player_id},
    )
    assert res3.status_code == 200
    data3 = res3.json()
    assert data3["patience"] == 0
    assert data3["status"] == "refused"
    assert (
        "patience is at its end" in data3["last_bark"].lower()
        or "shop" in data3["last_bark"].lower()
    )

    # 3. Subsequent gambit is rejected with error
    subsequent_res = client.post(
        f"/api/v1/haggling/{negotiation_id}/gambit",
        json={"character_id": "char_krag", "gambit": "flattery", "roll_value": 20},
        headers={"x-user-id": player_id},
    )
    assert subsequent_res.status_code == 400


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
            "item_name": "Potion of Invisibility",
            "base_price": 200,
            "initial_offer_gp": 140,
            "campaign_id": campaign_id,
            "temperament": "Stubborn",
        },
        headers={"x-user-id": player_id},
    )
    assert start_res.status_code == 200
    neg_id = start_res.json()["negotiation_id"]

    # 2. DM nudges mood with "soothe_merchant"
    soothe_res = client.patch(
        f"/api/v1/haggling/{neg_id}/dm-override",
        json={
            "action": "soothe_merchant",
            "narrative_bark": "The merchant takes a calming breath.",
        },
        headers={"x-user-id": dm_user_id},
    )
    assert soothe_res.status_code == 200
    assert soothe_res.json()["merchant_mood_score"] > 0
    assert soothe_res.json()["last_bark"] == "The merchant takes a calming breath."

    # 3. DM forces deal acceptance at 150 gold with custom narrative bark
    dm_accept_res = client.patch(
        f"/api/v1/haggling/{neg_id}/dm-override",
        json={
            "action": "force_accept",
            "override_price_gp": 150,
            "narrative_bark": "Torvin scowls, then nods in begrudging respect. Done.",
        },
        headers={"x-user-id": dm_user_id},
    )
    assert dm_accept_res.status_code == 200
    closed_data = dm_accept_res.json()
    assert closed_data["status"] == "completed"
    assert closed_data["counter_price"] == 150
    assert closed_data["last_bark"] == "Torvin scowls, then nods in begrudging respect. Done."

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
            "item_name": "Iron Helm",
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
