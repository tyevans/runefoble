"""Blackbox TDD integration test suite for Rules Compendium & Automated Encounter Builder.

Governed by Hard Invariant 7 (Blackbox TDD with Frontdoor Setup).
All assertions and setup operate strictly through public frontdoors:
- Public HTTP endpoints via TestClient(app) from rules_compendium.main
- FastMCP tool invocations via mcp.get_tool(...)
- SpiceDB Zanzibar authorization checks for homebrew rules
"""

import time
from uuid import uuid4

import pytest
from fastapi.testclient import TestClient
from gateway_mcp.server import mcp
from rules_compendium.dependencies import get_spicedb_client
from rules_compendium.main import app


@pytest.fixture
def client():
    with TestClient(app) as client:
        yield client


@pytest.mark.asyncio
async def test_blackbox_canonical_rule_search_sub_50ms(client: TestClient):
    """Verify hybrid BM25 and semantic rule search returns canonical results under 50ms."""
    # Warm up / verify initialization
    client.get("/healthz")
    client.get("/api/v1/compendium/rules/search?query=warmup")

    t0 = time.perf_counter()
    resp = client.get("/api/v1/compendium/rules/search?query=fire+damage+explosion")
    elapsed_ms = (time.perf_counter() - t0) * 1000

    assert resp.status_code == 200, resp.text
    data = resp.json()

    # Verify sub-50ms latency budget
    assert elapsed_ms < 50.0, f"Search took {elapsed_ms}ms, exceeding 50ms SLA"
    assert data["took_ms"] < 50.0
    assert data["results_count"] >= 1

    # Verify Fireball is returned in top results
    names = [r["name"] for r in data["results"]]
    assert "Fireball" in names
    fireball_result = next(r for r in data["results"] if r["name"] == "Fireball")
    assert fireball_result["category"] == "spell"
    assert fireball_result["is_homebrew"] is False


@pytest.mark.asyncio
async def test_blackbox_monster_and_condition_lookup(client: TestClient):
    """Verify direct lookups for monster stat blocks, spells, and condition mechanics."""
    # 1. Monster lookup
    m_resp = client.get("/api/v1/compendium/monsters/Goblin")
    assert m_resp.status_code == 200, m_resp.text
    goblin = m_resp.json()
    assert goblin["name"] == "Goblin"
    assert goblin["challenge_rating"] == 0.25
    assert goblin["xp"] == 50
    assert goblin["armor_class"] == 15
    assert goblin["hit_points"] == 7
    assert goblin["role"] == "skirmisher"

    # 2. Spell lookup
    s_resp = client.get("/api/v1/compendium/spells/Hold%20Person")
    assert s_resp.status_code == 200, s_resp.text
    spell = s_resp.json()
    assert spell["name"] == "Hold Person"
    assert spell["level"] == 2
    assert spell["school"] == "Enchantment"

    # 3. Condition lookup
    c_resp = client.get("/api/v1/compendium/conditions/Paralyzed")
    assert c_resp.status_code == 200, c_resp.text
    cond = c_resp.json()
    assert cond["name"] == "Paralyzed"
    assert len(cond["effects"]) >= 2
    assert any("Incapacitated" in e for e in cond["effects"])

    # 4. 404 on non-existent rule
    missing = client.get("/api/v1/compendium/monsters/NonExistentBeast99")
    assert missing.status_code == 404


@pytest.mark.asyncio
async def test_blackbox_cr_encounter_balancing_accuracy(client: TestClient):
    """Verify encounter builder calculates accurate XP thresholds and synergistic composition."""
    # Party of 4 level-3 adventurers:
    # Level 3 thresholds per character: Easy=75, Medium=150, Hard=225, Deadly=400
    # Expected party thresholds: Easy=300, Medium=600, Hard=900, Deadly=1600
    payload = {
        "party_levels": [3, 3, 3, 3],
        "target_difficulty": "Medium",
    }
    resp = client.post("/api/v1/compendium/encounters/balance", json=payload)
    assert resp.status_code == 200, resp.text
    data = resp.json()

    assert data["party_size"] == 4
    assert data["party_levels"] == [3, 3, 3, 3]
    assert data["target_difficulty"] == "Medium"

    thresholds = data["total_party_xp_threshold"]
    assert thresholds["easy"] == 300
    assert thresholds["medium"] == 600
    assert thresholds["hard"] == 900
    assert thresholds["deadly"] == 1600

    # Adjusted XP should fall in Medium or adjacent bracket and match multiplier math
    assert data["adjusted_xp"] >= thresholds["easy"]
    assert data["multiplier"] >= 1.0
    assert data["total_raw_xp"] > 0
    assert int(data["total_raw_xp"] * data["multiplier"]) == data["adjusted_xp"]
    assert len(data["monsters"]) >= 1

    # Verify tactical roles present
    roles = {m["role"] for m in data["monsters"]}
    assert any(r in roles for r in ["brute", "artillery", "controller", "skirmisher"])


@pytest.mark.asyncio
async def test_blackbox_party_size_multiplier_adjustments(client: TestClient):
    """Verify party size scaling: <3 increases multiplier tier, >=6 decreases multiplier tier."""
    # Solo player (party size 1 < 3)
    solo_resp = client.post(
        "/api/v1/compendium/encounters/balance",
        json={"party_levels": [5], "target_difficulty": "Hard"},
    )
    assert solo_resp.status_code == 200
    solo_data = solo_resp.json()
    assert solo_data["party_size"] == 1
    # 1 monster for small party shifts multiplier up from 1.0 to 1.5
    if solo_data["total_monster_count"] == 1:
        assert solo_data["multiplier"] == 1.5

    # Large party (size 6 >= 6)
    large_resp = client.post(
        "/api/v1/compendium/encounters/balance",
        json={"party_levels": [4, 4, 4, 4, 4, 4], "target_difficulty": "Medium"},
    )
    assert large_resp.status_code == 200
    large_data = large_resp.json()
    assert large_data["party_size"] == 6
    # Multiplier is stepped down for large parties
    if large_data["total_monster_count"] == 2:
        assert large_data["multiplier"] == 1.0  # stepped down from 1.5


@pytest.mark.asyncio
async def test_blackbox_spicedb_homebrew_registration_and_isolation(client: TestClient):
    """Verify homebrew rule registration is guarded by SpiceDB Zanzibar authorization."""
    campaign_id = str(uuid4())
    dm_user = f"dm-{uuid4().hex[:6]}"
    player_user = f"player-{uuid4().hex[:6]}"
    unauthorized_user = f"rando-{uuid4().hex[:6]}"

    spicedb = get_spicedb_client()

    # Assign DM role on campaign
    await spicedb.write_relationship(
        resource_type="campaign",
        resource_id=campaign_id,
        relation="dungeon_master",
        subject_type="user",
        subject_id=dm_user,
    )
    # Assign Player role on campaign
    await spicedb.write_relationship(
        resource_type="campaign",
        resource_id=campaign_id,
        relation="player",
        subject_type="user",
        subject_id=player_user,
    )

    homebrew_payload = {
        "campaign_id": campaign_id,
        "rule_type": "monster",
        "title": "Abyssal Shadowstalker",
        "content": {
            "challenge_rating": 3.0,
            "creature_type": "fiend",
            "size": "Medium",
            "armor_class": 16,
            "hit_points": 45,
            "xp": 700,
            "role": "skirmisher",
            "description": "A stealthy fiend summoned from the Shadowfell.",
        },
    }

    # 1. Unauthorized user registration attempt must be rejected (403 Forbidden)
    denied_resp = client.post(
        "/api/v1/compendium/homebrew",
        json=homebrew_payload,
        headers={"x-user-id": unauthorized_user},
    )
    assert denied_resp.status_code == 403
    assert "Forbidden" in denied_resp.json()["detail"]

    # 2. DM registers custom homebrew monster
    dm_resp = client.post(
        "/api/v1/compendium/homebrew",
        json=homebrew_payload,
        headers={"x-user-id": dm_user},
    )
    assert dm_resp.status_code == 200, dm_resp.text
    hb_data = dm_resp.json()
    assert hb_data["title"] == "Abyssal Shadowstalker"
    assert hb_data["author_id"] == dm_user
    assert hb_data["status"] == "registered"

    # 3. Campaign search with authorized user finds homebrew monster
    search_resp = client.get(
        f"/api/v1/compendium/rules/search?query=Shadowstalker&campaign_id={campaign_id}",
        headers={"x-user-id": player_user},
    )
    assert search_resp.status_code == 200
    search_results = search_resp.json()["results"]
    assert any(
        r["name"] == "Abyssal Shadowstalker" and r["is_homebrew"] is True for r in search_results
    )

    # 4. Search from external stranger without campaign permission CANNOT view homebrew
    ext_resp = client.get(
        f"/api/v1/compendium/rules/search?query=Shadowstalker&campaign_id={campaign_id}",
        headers={"x-user-id": unauthorized_user},
    )
    assert ext_resp.status_code == 200
    ext_results = ext_resp.json()["results"]
    assert not any(r["name"] == "Abyssal Shadowstalker" for r in ext_results)


@pytest.mark.asyncio
async def test_blackbox_fastmcp_compendium_tools():
    """Verify FastMCP compendium tools are registered and executable via FastMCP protocol entrypoint."""
    # 1. query_monster_stat_block tool
    monster_tool = mcp.get_tool("query_monster_stat_block")
    assert monster_tool is not None, "query_monster_stat_block must be registered in FastMCP"

    m_result = await monster_tool.run({"monster_name": "Bugbear"})
    # Result may be a dictionary or wrapped in CallToolResult
    res_data = m_result if isinstance(m_result, dict) else m_result.structured_content
    if res_data is None and hasattr(m_result, "content"):
        import json

        res_data = json.loads(m_result.content[0].text)

    assert res_data["status"] == "success"
    monster = res_data["monster"]
    assert monster["name"] == "Bugbear"
    assert monster["challenge_rating"] == 1.0
    assert monster["armor_class"] == 16
    assert monster["hit_points"] == 27
    assert monster["role"] == "brute"

    # 2. calculate_encounter_balance tool
    enc_tool = mcp.get_tool("calculate_encounter_balance")
    assert enc_tool is not None, "calculate_encounter_balance must be registered in FastMCP"

    enc_result = await enc_tool.run({"party_levels": [4, 4, 4], "target_difficulty": "Hard"})
    enc_data = enc_result if isinstance(enc_result, dict) else enc_result.structured_content
    if enc_data is None and hasattr(enc_result, "content"):
        import json

        enc_data = json.loads(enc_result.content[0].text)

    assert enc_data["status"] == "success"
    assert enc_data["party_size"] == 3
    assert enc_data["target_difficulty"] == "Hard"
    assert enc_data["adjusted_xp"] > 0
    assert len(enc_data["recommended_monsters"]) >= 1


def test_blackbox_openapi_spec(client: TestClient):
    """Verify OpenAPI specification compliance with Hard Invariant 5."""
    resp = client.get("/openapi.json")
    assert resp.status_code == 200
    spec = resp.json()
    assert "/api/v1/compendium/rules/search" in spec["paths"]
    assert "/api/v1/compendium/encounters/balance" in spec["paths"]
    assert "/api/v1/compendium/homebrew" in spec["paths"]
    assert "/api/v1/compendium/monsters/{name}" in spec["paths"]
