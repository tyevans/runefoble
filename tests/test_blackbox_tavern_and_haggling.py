"""Frontdoor blackbox tests for tavern minigames and merchant haggling.

Part of TASK-0103 / PRD-0014 / US-0047 / ADR-0003 / ADR-0006 / ADR-0011 / ADR-0013.
"""

from collections.abc import Iterator
from pathlib import Path

import pytest
from fastapi.testclient import TestClient
from game_session.main import app as session_app
from game_session.shared.streams import STREAM_TAVERN
from gateway_api.main import app as gateway_app
from voice_agent.main import app as voice_app

from tests.helpers.live_services import serve
from tests.helpers.voice_identity import voice_auth_headers
from tests.helpers.ws_identity import SIGNING_ISSUER, bearer

REPO_ROOT = Path(__file__).resolve().parent.parent


pytestmark = pytest.mark.usefixtures("trusted_ws_issuer")


def _owned_session(client: TestClient) -> str:
    """Create a campaign and one of its sessions through public routes. The caller owns both."""
    campaign = client.post("/api/v1/campaigns", json={"title": "Tavern Campaign"})
    assert campaign.status_code == 201, campaign.text
    session = client.post(
        f"/api/v1/campaigns/{campaign.json()['id']}/sessions", json={"title": "Tavern Night"}
    )
    assert session.status_code == 201, session.text
    return session.json()["id"]


@pytest.fixture
def session_client():
    return TestClient(
        session_app, headers={"Authorization": f"Bearer {SIGNING_ISSUER.mint('test-user')}"}
    )


@pytest.fixture
def live_voice_agent(monkeypatch, trusted_voice_issuer):
    """Run voice_agent as a real HTTP upstream for the drink DSP call (ADR-0007)."""
    with serve(voice_app) as voice_url:
        monkeypatch.setenv("RUNEFOBLE_VOICE_AGENT_URL", voice_url)
        yield voice_url


@pytest.fixture
def gateway_client(game_session_upstream) -> Iterator[TestClient]:
    """Gateway client with the lifespan entered after game_session is served."""
    with TestClient(gateway_app) as client:
        yield client


def test_tavern_parlor_microfrontend_manifest(session_client):
    """Verify microfrontend manifest advertises runefoble-tavern-parlor."""
    res = session_client.get("/ui/manifest")
    assert res.status_code == 200
    data = res.json()
    assert data["service"] == "game_session"
    assert data["package"] == "@runefoble/game-session-ui"
    assert "runefoble-tavern-parlor" in data["components"]


def test_blackbox_liars_dice_minigame_flow(session_client, mock_bus):
    """Test full Liar's Dice minigame: challenge, turns, bluff call, and victory payout."""
    session_id = _owned_session(session_client)

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
    assert any(
        "runefoble.events.tavern.minigame_started" in entry[1].get("event_type", "")
        for entry in entries
    )
    assert any(
        "runefoble.events.tavern.minigame_turn_taken" in entry[1].get("event_type", "")
        for entry in entries
    )
    assert any(
        "runefoble.events.tavern.minigame_ended" in entry[1].get("event_type", "")
        for entry in entries
    )


def test_blackbox_drinking_contest_and_dsp_speech(session_client, mock_bus, live_voice_agent):
    """Test drinking contest with progressive intoxication DC and DSP speech conditioning."""
    session_id = _owned_session(session_client)

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
        headers=voice_auth_headers("test-user"),
    )
    assert d1_res.status_code == 200
    assert d1_res.json()["result"]["intoxication_level"] == "sober"

    # Drink 2: roll 5 vs DC 12 -> tipsy
    d2_res = session_client.post(
        f"/api/v1/sessions/{session_id}/tavern/games/{game_id}/turn",
        json={"actor_id": "char_bram", "action_type": "drink", "con_roll": 5},
        headers=voice_auth_headers("test-user"),
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
        headers=voice_auth_headers("test-user"),
    )
    assert d3_res.status_code == 200
    d3_data = d3_res.json()["result"]
    assert d3_data["intoxication_level"] == "drunk"
    assert "drunk" in d3_data["dsp_filters"]
    assert d3_data["voice_dsp"] is not None
    assert "conditioned_text" in d3_data["voice_dsp"]

    # Verify IntoxicationLevelChanged published
    entries = mock_bus.streams.get(STREAM_TAVERN, [])
    assert any(
        "runefoble.events.tavern.intoxication_level_changed" in entry[1].get("event_type", "")
        for entry in entries
    )


def test_blackbox_merchant_haggling_stubborn_greedy(session_client, mock_bus):
    """Test US-0047 Scenario 2: Bram haggles 50g quote to 35g against stubborn dwarven blacksmith."""
    session_id = _owned_session(session_client)
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
    assert any(
        "runefoble.events.tavern.haggling_negotiated" in entry[1].get("event_type", "")
        for entry in entries
    )

    # Query merchant profile
    m_res = session_client.get(f"/api/v1/merchants/{merchant_id}")
    assert m_res.status_code == 200
    assert m_res.json()["successful_deals"] >= 1


def test_blackbox_merchant_insult_lowball(session_client):
    """Test severe lowball offer triggering merchant insult outcome."""
    session_id = _owned_session(session_client)
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


def test_blackbox_gateway_zanzibar_authorization(gateway_client, trusted_ws_issuer):
    """Verify Gateway Zanzibar authorization enforcement for tavern minigames and merchant haggling.

    Membership is created through frontdoors only: the owner creates the campaign,
    issues a player invite, and the player redeems it.
    """
    owner_headers = bearer("user_dm", issuer=trusted_ws_issuer)
    user_headers = bearer("user_bram", issuer=trusted_ws_issuer)

    create_res = gateway_client.post(
        "/api/v1/campaigns",
        json={"title": "Tavern Nights", "setting": "Waterdeep", "system": "5e"},
        headers=owner_headers,
    )
    assert create_res.status_code == 201
    camp_id = create_res.json()["id"]

    invite_res = gateway_client.post(
        f"/api/v1/campaigns/{camp_id}/invites",
        json={"role": "player"},
        headers=owner_headers,
    )
    assert invite_res.status_code == 201
    join_res = gateway_client.post(
        "/api/v1/campaigns/join",
        json={"invite_token": invite_res.json()["token"]},
        headers=user_headers,
    )
    assert join_res.status_code == 200

    sessions_res = gateway_client.get(
        f"/api/v1/campaigns/{camp_id}/sessions", headers=owner_headers
    )
    assert sessions_res.status_code == 200
    session_id = sessions_res.json()[0]["id"]

    # 1. Start minigame via gateway with authorized player
    start_res = gateway_client.post(
        f"/api/v1/sessions/{session_id}/tavern/games",
        json={"game_type": "liars_dice", "wager_gold": 10, "initiator_id": "bram"},
        headers=user_headers,
    )
    assert start_res.status_code == 200
    assert start_res.json()["wager_gold"] == 10
    assert start_res.json()["initiator_id"] == "bram"

    # 2. Unauthorized user denied
    denied_res = gateway_client.post(
        f"/api/v1/sessions/{session_id}/tavern/games",
        json={"game_type": "liars_dice", "wager_gold": 10, "initiator_id": "bram"},
        headers=bearer("unauthorized_stranger", issuer=trusted_ws_issuer),
    )
    assert denied_res.status_code == 403

    # 3. Haggle without an establishment is refused by the owner (establishment_id is required)
    haggle_res = gateway_client.post(
        f"/api/v1/sessions/{session_id}/merchants/merchant_dwarf/haggle",
        json={
            "character_id": "bram",
            "campaign_id": camp_id,
            "establishment_id": "",
            "item_id": "shield",
            "item_name": "Shield",
            "base_price": 50,
            "offered_price": 35,
            "temperament": "stubborn_greedy",
        },
        headers=user_headers,
    )
    assert haggle_res.status_code == 422
