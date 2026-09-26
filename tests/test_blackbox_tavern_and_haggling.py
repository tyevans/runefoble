"""Frontdoor blackbox tests for tavern minigames and merchant haggling.

Part of TASK-0103 / PRD-0014 / US-0047 / ADR-0003 / ADR-0006 / ADR-0011 / ADR-0013.
"""

from pathlib import Path
from uuid import uuid4

import pytest
from fastapi.testclient import TestClient
from game_session.dependencies import (
    STREAM_TAVERN,
)
from game_session.dependencies import (
    set_event_bus as set_session_event_bus,
)
from game_session.dependencies import (
    set_spicedb_client as set_session_spicedb,
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
    set_session_event_bus(bus)
    yield redis_client
    set_session_event_bus(None)


@pytest.fixture
def session_client():
    mock_spicedb = MockSpiceDBClient()
    set_session_spicedb(mock_spicedb)
    return TestClient(session_app)


@pytest.fixture
def gateway_client():
    mock_spicedb = MockSpiceDBClient()
    set_gateway_spicedb(mock_spicedb)
    return TestClient(gateway_app)


def test_tavern_parlor_microfrontend_manifest_and_files(session_client):
    """Verify microfrontend manifest advertises runefoble-tavern-parlor and files exist."""
    res = session_client.get("/ui/manifest")
    assert res.status_code == 200
    data = res.json()
    assert data["service"] == "game_session"
    assert data["package"] == "@runefoble/game-session-ui"
    assert "runefoble-tavern-parlor" in data["components"]

    ui_dir = REPO_ROOT / "services" / "game_session" / "ui" / "src"
    comp_file = ui_dir / "runefoble-tavern-parlor.ts"
    stories_file = ui_dir / "runefoble-tavern-parlor.stories.ts"
    styles_file = ui_dir / "runefoble-tavern-parlor.styles.ts"

    assert comp_file.is_file(), "Tavern parlor component file must exist"
    assert stories_file.is_file(), "Tavern parlor Storybook file must exist"
    assert styles_file.is_file(), "Tavern parlor styles file must exist"

    comp_code = comp_file.read_text(encoding="utf-8")
    assert "@customElement('runefoble-tavern-parlor')" in comp_code
    assert "minigame-turn-taken" in comp_code
    assert "liars-dice-challenged" in comp_code
    assert "drink-taken" in comp_code
    assert "haggling-submitted" in comp_code


def test_blackbox_liars_dice_minigame_flow(session_client, mock_bus):
    """Test full Liar's Dice minigame: challenge, turns, bluff call, and victory payout."""
    session_id = str(uuid4())

    # 1. Challenge NPC pirate with 10 gold wager
    start_payload = {
        "game_type": "liars_dice",
        "wager_gold": 10,
        "initiator_id": "char_bram",
        "challenger_id": "npc_pirate",
    }
    start_res = session_client.post(
        f"/api/v1/sessions/{session_id}/tavern/games",
        json=start_payload,
    )
    assert start_res.status_code == 200, start_res.text
    game_state = start_res.json()
    game_id = game_state["game_id"]
    assert game_state["status"] == "active"
    assert game_state["wager_gold"] == 10
    assert "char_bram" in game_state["player_hands"]
    assert len(game_state["player_hands"]["char_bram"]) == 5

    # 2. Bram makes opening bid: 2 threes
    bid1_res = session_client.post(
        f"/api/v1/sessions/{session_id}/tavern/games/{game_id}/turn",
        json={"actor_id": "char_bram", "action_type": "bid", "quantity": 2, "face": 3},
    )
    assert bid1_res.status_code == 200
    assert bid1_res.json()["result"]["bid"]["quantity"] == 2
    assert bid1_res.json()["state"]["current_turn_actor"] == "npc_pirate"

    # 3. Pirate raises bid: 3 fours
    bid2_res = session_client.post(
        f"/api/v1/sessions/{session_id}/tavern/games/{game_id}/turn",
        json={"actor_id": "npc_pirate", "action_type": "bid", "quantity": 3, "face": 4},
    )
    assert bid2_res.status_code == 200
    assert bid2_res.json()["state"]["current_turn_actor"] == "char_bram"

    # 4. Bram calls bluff ('Challenge / Liar!')
    call_res = session_client.post(
        f"/api/v1/sessions/{session_id}/tavern/games/{game_id}/turn",
        json={"actor_id": "char_bram", "action_type": "challenge"},
    )
    assert call_res.status_code == 200
    res_data = call_res.json()
    assert res_data["state"]["status"] == "completed"
    assert res_data["result"]["payout"] == 20
    assert res_data["result"]["voice_bark"] is not None

    # 5. Verify domain events published on Redis Streams
    entries = mock_bus.streams.get(STREAM_TAVERN, [])
    assert any("MinigameStarted" in entry[1].get("event_type", "") for entry in entries)
    assert any("MinigameTurnTaken" in entry[1].get("event_type", "") for entry in entries)
    assert any("MinigameEnded" in entry[1].get("event_type", "") for entry in entries)


def test_blackbox_drinking_contest_and_dsp_speech(session_client, mock_bus):
    """Test drinking contest with progressive intoxication DC and DSP speech conditioning."""
    session_id = str(uuid4())

    start_res = session_client.post(
        f"/api/v1/sessions/{session_id}/tavern/games",
        json={
            "game_type": "drinking_contest",
            "wager_gold": 15,
            "initiator_id": "char_bram",
            "challenger_id": "npc_dwarf",
        },
    )
    assert start_res.status_code == 200
    game_id = start_res.json()["game_id"]

    # Drink 1: roll 18 vs DC 10 -> sober
    d1_res = session_client.post(
        f"/api/v1/sessions/{session_id}/tavern/games/{game_id}/turn",
        json={"actor_id": "char_bram", "action_type": "drink", "con_roll": 18},
    )
    assert d1_res.status_code == 200
    assert d1_res.json()["result"]["intoxication_level"] == "sober"

    # Drink 2: roll 5 vs DC 12 -> tipsy
    d2_res = session_client.post(
        f"/api/v1/sessions/{session_id}/tavern/games/{game_id}/turn",
        json={"actor_id": "char_bram", "action_type": "drink", "con_roll": 5},
    )
    assert d2_res.json()["result"]["intoxication_level"] == "tipsy"

    # Drink 3: roll 6 vs DC 14 with speech text -> drunk with DSP filters
    speech_phrase = "I can drink the whole tavern under the table!"
    d3_res = session_client.post(
        f"/api/v1/sessions/{session_id}/tavern/games/{game_id}/turn",
        json={
            "actor_id": "char_bram",
            "action_type": "drink",
            "con_roll": 6,
            "speech_text": speech_phrase,
        },
    )
    assert d3_res.status_code == 200
    d3_data = d3_res.json()["result"]
    assert d3_data["intoxication_level"] == "drunk"
    assert "drunk" in d3_data["dsp_filters"]
    assert d3_data["voice_dsp"] is not None
    assert "conditioned_text" in d3_data["voice_dsp"]

    # Verify IntoxicationLevelChanged published
    entries = mock_bus.streams.get(STREAM_TAVERN, [])
    assert any("IntoxicationLevelChanged" in entry[1].get("event_type", "") for entry in entries)


def test_blackbox_merchant_haggling_stubborn_greedy(session_client, mock_bus):
    """Test US-0047 Scenario 2: Bram haggles 50g quote to 35g against stubborn dwarven blacksmith."""
    session_id = str(uuid4())
    merchant_id = "merchant_thorin_blacksmith"

    haggle_payload = {
        "character_id": "char_bram",
        "item_name": "Reinforced Shield",
        "base_price": 50,
        "offered_price": 35,
        "charisma_modifier": 3,
        "dialogue": "I am Bram the Tinkerer. Your dwarven steel is legendary, but 35 gold is a fair purse today.",
    }

    haggle_res = session_client.post(
        f"/api/v1/sessions/{session_id}/merchants/{merchant_id}/haggle",
        params={"temperament": "stubborn_greedy"},
        json=haggle_payload,
    )
    assert haggle_res.status_code == 200, haggle_res.text
    haggle_data = haggle_res.json()

    assert haggle_data["merchant_id"] == merchant_id
    assert haggle_data["temperament"] == "stubborn_greedy"
    assert haggle_data["outcome"] == "countered"
    assert haggle_data["counter_price"] == 42
    assert haggle_data["agreed_price"] == 42
    assert "42 gold" in haggle_data["voice_bark"]

    # Verify HagglingNegotiated published
    entries = mock_bus.streams.get(STREAM_TAVERN, [])
    assert any("HagglingNegotiated" in entry[1].get("event_type", "") for entry in entries)

    # Query merchant profile
    m_res = session_client.get(f"/api/v1/merchants/{merchant_id}")
    assert m_res.status_code == 200
    assert m_res.json()["successful_deals"] >= 1


def test_blackbox_merchant_insult_lowball(session_client):
    """Test severe lowball offer triggering merchant insult outcome."""
    session_id = str(uuid4())
    merchant_id = "merchant_krag_hostile"

    haggle_res = session_client.post(
        f"/api/v1/sessions/{session_id}/merchants/{merchant_id}/haggle",
        params={"temperament": "hostile"},
        json={
            "character_id": "char_bram",
            "item_name": "Masterwork Crossbow",
            "base_price": 100,
            "offered_price": 20,
            "charisma_modifier": 0,
        },
    )
    assert haggle_res.status_code == 200
    res = haggle_res.json()
    assert res["outcome"] == "insulted"
    assert res["agreed_price"] is None
    assert res["mood_score"] < 0


def test_blackbox_gateway_zanzibar_authorization(gateway_client):
    """Verify Gateway Zanzibar authorization enforcement for tavern minigames and merchant haggling."""
    camp_id = f"camp-tavern-{uuid4().hex[:6]}"
    user_id = "user_bram"

    # Assign player role to Bram
    role_res = gateway_client.post(
        f"/api/v1/campaigns/{camp_id}/roles",
        json={"user_id": user_id, "role": "player"},
    )
    assert role_res.status_code == 200

    # 1. Start minigame via gateway with authorized player
    start_res = gateway_client.post(
        f"/api/v1/sessions/{camp_id}/tavern/games",
        json={"game_type": "liars_dice", "wager_gold": 10, "initiator_id": "bram"},
        headers={"X-User-Id": user_id},
    )
    assert start_res.status_code == 200
    assert start_res.json()["wager_pot"] == 20

    # 2. Unauthorized user denied
    denied_res = gateway_client.post(
        f"/api/v1/sessions/{camp_id}/tavern/games",
        json={"game_type": "liars_dice", "wager_gold": 10, "initiator_id": "bram"},
        headers={"X-User-Id": "unauthorized_stranger"},
    )
    assert denied_res.status_code == 403

    # 3. Haggle via gateway with authorized player
    haggle_res = gateway_client.post(
        f"/api/v1/sessions/{camp_id}/merchants/merchant_dwarf/haggle",
        json={
            "character_id": "bram",
            "item_name": "Shield",
            "base_price": 50,
            "offered_price": 35,
            "temperament": "stubborn_greedy",
        },
        headers={"X-User-Id": user_id},
    )
    assert haggle_res.status_code == 200
    assert haggle_res.json()["counter_price"] == 42
