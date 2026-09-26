"""Frontdoor blackbox tests for downtime activities, alchemical crafting, and stronghold engine.

Governed by:
- ADR-0003: UV Monorepo Workspace for Python BCs
- ADR-0006: Redis Streams Event Bus
- ADR-0011: eventsource-py Core Event Sourcing
- ADR-0013: Microfrontend Architecture and Service Component Vendoring
- Hard Invariant 7: Blackbox TDD with frontdoor setup (zero backdoor state manipulation)
"""

from pathlib import Path
from uuid import uuid4

import pytest
from character_sheet.dependencies import (
    STREAM_CRAFTING,
)
from character_sheet.dependencies import (
    set_event_bus as set_char_event_bus,
)
from character_sheet.main import app as character_app
from fastapi.testclient import TestClient
from game_session.dependencies import (
    STREAM_SESSION,
    STREAM_STRONGHOLD,
)
from game_session.dependencies import (
    set_event_bus as set_session_event_bus,
)
from game_session.main import app as session_app
from gateway_api.auth import set_spicedb_client as set_gateway_spicedb
from gateway_api.main import app as gateway_app
from runefoble_auth.spicedb import MockSpiceDBClient
from runefoble_platform.mock_redis import MockAsyncRedis
from runefoble_platform.redis_bus import RedisStreamsEventBus

REPO_ROOT = Path(__file__).resolve().parent.parent


@pytest.fixture
def mock_bus():
    redis_client = MockAsyncRedis()
    bus = RedisStreamsEventBus(client=redis_client)
    set_char_event_bus(bus)
    set_session_event_bus(bus)
    yield redis_client
    set_char_event_bus(None)
    set_session_event_bus(None)


@pytest.fixture
def char_client():
    return TestClient(character_app)


@pytest.fixture
def session_client():
    return TestClient(session_app)


@pytest.fixture
def gateway_client():
    return TestClient(gateway_app)


def test_campfire_crafting_microfrontend_manifest_and_files(session_client):
    """Verify microfrontend manifest advertises runefoble-campfire-crafting and files exist."""
    # 1. Manifest discovery frontdoor
    res = session_client.get("/ui/manifest")
    assert res.status_code == 200
    data = res.json()
    assert data["service"] == "game_session"
    assert data["package"] == "@runefoble/game-session-ui"
    assert "runefoble-campfire-crafting" in data["components"]

    # 2. Component and Storybook story source files
    comp_file = (
        REPO_ROOT / "services" / "game_session" / "ui" / "src" / "runefoble-campfire-crafting.ts"
    )
    stories_file = (
        REPO_ROOT
        / "services"
        / "game_session"
        / "ui"
        / "src"
        / "runefoble-campfire-crafting.stories.ts"
    )
    styles_file = (
        REPO_ROOT
        / "services"
        / "game_session"
        / "ui"
        / "src"
        / "runefoble-campfire-crafting.styles.ts"
    )

    assert comp_file.is_file(), "Campfire crafting component file must exist"
    assert stories_file.is_file(), "Campfire crafting Storybook file must exist"
    assert styles_file.is_file(), "Campfire crafting styles file must exist"

    comp_code = comp_file.read_text(encoding="utf-8")
    assert "@customElement('runefoble-campfire-crafting')" in comp_code
    assert "reagents-combined" in comp_code
    assert "campfire-rest-requested" in comp_code
    assert "stronghold-upgrade-requested" in comp_code


def test_blackbox_reagent_recipes_and_catalogue(char_client):
    """Verify public query endpoints for reagents, affinities, and known recipes."""
    # Recipes query
    rec_res = char_client.get("/api/v1/crafting/recipes")
    assert rec_res.status_code == 200
    recipes = rec_res.json()
    recipe_names = [r["name"] for r in recipes]
    assert "Radiant Smoke Pellet" in recipe_names
    assert "Elixir of Luminescence" in recipe_names

    # Reagents catalogue query
    reag_res = char_client.get("/api/v1/crafting/reagents")
    assert reag_res.status_code == 200
    reag_data = reag_res.json()
    assert "Glowmoss Extract" in reag_data["reagents"]
    assert "Volcano Ash" in reag_data["reagents"]
    assert "purified_water" in reag_data["catalysts"]


def test_blackbox_alchemical_crafting_success_flow(char_client, mock_bus):
    """Test reagent combination success generating novel item and updating inventory."""
    # 1. Create character Bram the Tinkerer
    create_res = char_client.post(
        "/api/v1/characters",
        json={"name": "Bram the Tinkerer", "character_class": "Artificer", "max_hp": 24},
    )
    assert create_res.status_code == 200
    char_id = create_res.json()["character_id"]

    # 2. Add reagents to character inventory
    char_client.post(
        f"/api/v1/characters/{char_id}/inventory/add",
        json={"name": "Glowmoss Extract", "quantity": 1, "weight_lbs": 0.2},
    )
    char_client.post(
        f"/api/v1/characters/{char_id}/inventory/add",
        json={"name": "Volcano Ash", "quantity": 1, "weight_lbs": 0.5},
    )

    # 3. Combine reagents via public HTTP frontdoor
    combine_payload = {
        "character_id": char_id,
        "reagents": ["Glowmoss Extract", "Volcano Ash"],
        "catalyst": "purified_water",
    }
    combine_res = char_client.post("/api/v1/crafting/recipes/combine", json=combine_payload)
    assert combine_res.status_code == 200, combine_res.text
    result = combine_res.json()

    assert result["outcome"] == "success"
    assert result["item_name"] == "Radiant Smoke Pellet"
    assert "radiant" in result["tags"]
    assert "obscurement" in result["tags"]

    # 4. Verify character inventory contains created item
    char_res = char_client.get(f"/api/v1/characters/{char_id}")
    assert char_res.status_code == 200
    char_data = char_res.json()
    inv_names = [i["name"] for i in char_data["inventory"].values()]
    assert "Radiant Smoke Pellet" in inv_names

    # 5. Verify crafting history
    hist_res = char_client.get(f"/api/v1/crafting/{char_id}/history")
    assert hist_res.status_code == 200
    hist = hist_res.json()
    assert hist["total_crafts"] >= 1
    assert hist["successful_crafts"] >= 1
    assert "Radiant Smoke Pellet" in hist["discovered_recipes"]

    # 6. Verify domain events published on Redis Streams
    entries = mock_bus.streams.get(STREAM_CRAFTING, [])
    assert any("CraftingAttempted" in entry[1].get("event_type", "") for entry in entries)
    assert any("CraftingSucceeded" in entry[1].get("event_type", "") for entry in entries)


def test_blackbox_alchemical_crafting_volatile_mishap(char_client, mock_bus):
    """Test volatile reaction mishap triggering damage and condition."""
    # 1. Create character
    create_res = char_client.post(
        "/api/v1/characters",
        json={"name": "Novice Apprentice", "character_class": "Wizard", "max_hp": 16},
    )
    assert create_res.status_code == 200
    char_id = create_res.json()["character_id"]
    initial_hp = create_res.json()["current_hp"]

    # 2. Force volatile mishap via public frontdoor
    mishap_payload = {
        "character_id": char_id,
        "reagents": ["Volcano Ash", "Wyrm Blood"],
        "force_mishap": True,
    }
    combine_res = char_client.post("/api/v1/crafting/recipes/combine", json=mishap_payload)
    assert combine_res.status_code == 200
    result = combine_res.json()

    assert result["outcome"] == "mishap"
    assert result["mishap"] is not None
    assert result["character_current_hp"] < initial_hp

    # Verify character took mishap damage
    char_res = char_client.get(f"/api/v1/characters/{char_id}")
    assert char_res.json()["current_hp"] == result["character_current_hp"]

    # Verify event bus
    entries = mock_bus.streams.get(STREAM_CRAFTING, [])
    assert any("CraftingMishapOccurred" in entry[1].get("event_type", "") for entry in entries)


def test_blackbox_stronghold_campsite_progression(session_client, mock_bus):
    """Test persistent campsite facility upgrades and team rest boons."""
    camp_id = str(uuid4())

    # 1. Initial stronghold state
    init_res = session_client.get(f"/api/v1/campaigns/{camp_id}/stronghold")
    assert init_res.status_code == 200
    assert init_res.json()["facilities"]["watchtower"] == 0

    # 2. Upgrade Watchtower to Tier 1
    upg1_res = session_client.post(
        f"/api/v1/campaigns/{camp_id}/stronghold/upgrade",
        json={"facility_id": "watchtower", "gold_spent": 100, "materials_spent": {"wood": 20}},
    )
    assert upg1_res.status_code == 200
    upg1 = upg1_res.json()
    assert upg1["new_tier"] == 1
    assert "Passive Perception" in upg1["unlocked_boon"]
    assert upg1["state"]["facilities"]["watchtower"] == 1

    # 3. Upgrade Herbal Drying Rack to Tier 1
    upg2_res = session_client.post(
        f"/api/v1/campaigns/{camp_id}/stronghold/upgrade",
        json={"facility_id": "herbal_rack", "gold_spent": 75, "materials_spent": {"flora": 15}},
    )
    assert upg2_res.status_code == 200
    assert upg2_res.json()["new_tier"] == 1

    # 4. Check active boons endpoint
    boons_res = session_client.get(f"/api/v1/campaigns/{camp_id}/stronghold/boons")
    assert boons_res.status_code == 200
    active_boons = boons_res.json()["active_boons"]
    assert any("Passive Perception" in b for b in active_boons)
    assert any("Rest Healing" in b for b in active_boons)

    # 5. Verify StrongholdUpgraded published
    entries = mock_bus.streams.get(STREAM_STRONGHOLD, [])
    assert any("StrongholdUpgraded" in entry[1].get("event_type", "") for entry in entries)


def test_blackbox_campfire_rest_interlude_with_boons(session_client, mock_bus):
    """Test campfire rest sequence with collaborative storytelling prompts and resting buffs."""
    camp_id = uuid4()

    # 1. Initialize session and camp upgrade
    create_res = session_client.post(
        "/api/v1/sessions/create",
        json={"campaign_id": str(camp_id), "title": "Campfire Rest Chapter", "dm_id": "dm_evelyn"},
    )
    assert create_res.status_code == 200
    session_id = create_res.json()["session_id"]

    # Upgrade watchtower for campaign
    session_client.post(
        f"/api/v1/campaigns/{camp_id}/stronghold/upgrade",
        json={"facility_id": "watchtower", "gold_spent": 100},
    )

    # 2. Get storytelling prompts
    prompts_res = session_client.get(f"/api/v1/sessions/{session_id}/rest/prompts")
    assert prompts_res.status_code == 200
    assert len(prompts_res.json()["prompts"]) >= 3

    # 3. Initiate campfire rest
    rest_payload = {
        "rest_type": "long",
        "storytelling_prompt": "Tell of the first monster that frightened your character.",
    }
    rest_res = session_client.post(
        f"/api/v1/sessions/{session_id}/rest/campfire",
        json=rest_payload,
    )
    assert rest_res.status_code == 200, rest_res.text
    rest_data = rest_res.json()

    assert rest_data["status"] == "completed"
    assert rest_data["rest_type"] == "long"
    assert "Tell of the first monster" in rest_data["storytelling_prompt"]

    # Verify rest boons: includes baseline + stronghold boons
    boons = rest_data["boons_applied"]
    assert any("Full HP Restored" in b for b in boons)
    assert any("Campfire Camaraderie" in b for b in boons)
    assert any("Passive Perception" in b for b in boons)

    # Verify CampfireRestCompleted published
    entries = mock_bus.streams.get(STREAM_SESSION, [])
    assert any("CampfireRestCompleted" in entry[1].get("event_type", "") for entry in entries)


def test_blackbox_gateway_zanzibar_authorization(gateway_client):
    """Verify Gateway Zanzibar authorization enforcement for downtime and crafting endpoints."""
    mock_spicedb = MockSpiceDBClient()
    set_gateway_spicedb(mock_spicedb)

    camp_id = f"camp-auth-{uuid4().hex[:6]}"
    user_id = "user_bram"

    # Assign player role to Bram
    role_res = gateway_client.post(
        f"/api/v1/campaigns/{camp_id}/roles",
        json={"user_id": user_id, "role": "player"},
    )
    assert role_res.status_code == 200

    # 1. GET Stronghold with authorized player
    get_res = gateway_client.get(
        f"/api/v1/campaigns/{camp_id}/stronghold",
        headers={"X-User-Id": user_id},
    )
    assert get_res.status_code == 200
    assert get_res.json()["campaign_id"] == camp_id

    # 2. Unauthorized user denied
    denied_res = gateway_client.get(
        f"/api/v1/campaigns/{camp_id}/stronghold",
        headers={"X-User-Id": "unauthorized_stranger"},
    )
    assert denied_res.status_code == 403

    # 3. Upgrade Stronghold via gateway
    upg_res = gateway_client.post(
        f"/api/v1/campaigns/{camp_id}/stronghold/upgrade",
        json={"facility_id": "watchtower", "gold_spent": 100},
        headers={"X-User-Id": user_id},
    )
    assert upg_res.status_code == 200
    assert upg_res.json()["status"] == "upgraded"

    # 4. Crafting combine via gateway
    craft_res = gateway_client.post(
        "/api/v1/crafting/recipes/combine",
        json={
            "character_id": str(uuid4()),
            "reagents": ["Glowmoss Extract", "Volcano Ash"],
        },
        headers={"X-User-Id": user_id},
        params={"campaign_id": camp_id},
    )
    assert craft_res.status_code == 200
    assert craft_res.json()["item_name"] == "Radiant Smoke Pellet"
