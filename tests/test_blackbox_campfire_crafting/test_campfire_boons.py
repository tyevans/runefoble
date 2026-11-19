"""Blackbox tests for campsite progression, campfire resting boons, and UI manifest.

Governed by ADR-0003, ADR-0006, ADR-0007, ADR-0011, and Hard Invariant 7.
"""

from __future__ import annotations

from fastapi.testclient import TestClient
from game_session.events import STREAM_STRONGHOLD

from tests.helpers.campaign_setup import create_owned_campaign


def _fund(client: TestClient, campaign_id: str, gold: int, materials: dict[str, int]) -> None:
    """Fund the campsite treasury through the public deposit route."""
    res = client.post(
        f"/api/v1/campaigns/{campaign_id}/stronghold/deposit",
        json={"gold": gold, "materials": materials},
    )
    assert res.status_code == 200, res.text


def test_campfire_crafting_microfrontend_manifest(session_client: TestClient):
    """Verify microfrontend manifest advertises runefoble-campfire-crafting."""
    res = session_client.get("/ui/manifest")
    assert res.status_code == 200
    data = res.json()
    assert data["service"] == "game_session"
    assert data["package"] == "@runefoble/game-session-ui"
    assert "runefoble-campfire-crafting" in data["components"]


def test_blackbox_stronghold_campsite_progression(session_client: TestClient, mock_bus):
    """Test persistent campsite facility upgrades and team rest boons."""
    camp_id = create_owned_campaign(session_client)

    init_res = session_client.get(f"/api/v1/campaigns/{camp_id}/stronghold")
    assert init_res.status_code == 200
    assert init_res.json()["facilities"]["watchtower"] == 0

    _fund(session_client, camp_id, gold=175, materials={"wood": 20, "flora": 15})

    upg1_res = session_client.post(
        f"/api/v1/campaigns/{camp_id}/stronghold/upgrade",
        json={"facility_id": "watchtower"},
    )
    assert upg1_res.status_code == 200
    upg1 = upg1_res.json()
    assert upg1["new_tier"] == 1
    assert "Passive Perception" in upg1["unlocked_boon"]
    assert upg1["state"]["facilities"]["watchtower"] == 1

    upg2_res = session_client.post(
        f"/api/v1/campaigns/{camp_id}/stronghold/upgrade",
        json={"facility_id": "herbal_rack"},
    )
    assert upg2_res.status_code == 200
    assert upg2_res.json()["new_tier"] == 1

    boons_res = session_client.get(f"/api/v1/campaigns/{camp_id}/stronghold/boons")
    assert boons_res.status_code == 200
    active_boons = boons_res.json()["active_boons"]
    assert any("Passive Perception" in b for b in active_boons)
    assert any("Rest Healing" in b for b in active_boons)

    entries = mock_bus.streams.get(STREAM_STRONGHOLD, [])
    assert any(
        "runefoble.events.downtime.stronghold_upgraded" in entry[1].get("event_type", "")
        for entry in entries
    )


def test_blackbox_campfire_rest_interlude_with_boons(session_client: TestClient, mock_bus):
    """Test campfire rest sequence with collaborative storytelling prompts and resting buffs."""
    camp_id = create_owned_campaign(session_client)

    create_res = session_client.post(
        "/api/v1/sessions/create",
        json={
            "campaign_id": camp_id,
            "title": "Campfire Rest Chapter",
            "dm_id": "dm_evelyn",
        },
    )
    assert create_res.status_code == 200
    session_id = create_res.json()["session_id"]

    _fund(session_client, camp_id, gold=100, materials={"wood": 20})
    upgrade_res = session_client.post(
        f"/api/v1/campaigns/{camp_id}/stronghold/upgrade",
        json={"facility_id": "watchtower"},
    )
    assert upgrade_res.status_code == 200, upgrade_res.text

    prompts_res = session_client.get(f"/api/v1/sessions/{session_id}/rest/prompts")
    assert prompts_res.status_code == 200
    assert len(prompts_res.json()["prompts"]) >= 3

    rest_res = session_client.post(
        f"/api/v1/sessions/{session_id}/rest/campfire",
        json={
            "rest_type": "long",
            "storytelling_prompt": "Tell of the first monster that frightened your character.",
        },
    )
    assert rest_res.status_code == 200, rest_res.text
    rest_data = rest_res.json()

    assert rest_data["status"] == "completed"
    assert rest_data["rest_type"] == "long"
    assert "Tell of the first monster" in rest_data["storytelling_prompt"]

    boons = rest_data["boons_applied"]
    assert any("Full HP Restored" in b for b in boons)
    assert any("Campfire Camaraderie" in b for b in boons)
    assert any("Passive Perception" in b for b in boons)
