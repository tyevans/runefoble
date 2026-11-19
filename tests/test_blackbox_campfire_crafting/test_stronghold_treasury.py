"""Blackbox tests for stronghold treasury funding, tier-table upgrade cost, and shortfall refusal (TASK-0774, TASK-0778).

Setup and assertions use public HTTP routes only. Governed by ADR-0011 (the command decides,
the `@handles` method applies the recorded change) and Hard Invariant 7.
"""

from __future__ import annotations

from fastapi.testclient import TestClient
from game_session.events import STREAM_STRONGHOLD

from tests.helpers.campaign_setup import create_owned_campaign
from tests.helpers.ws_identity import SIGNING_ISSUER


def _deposit(client: TestClient, campaign_id: str, gold: int, materials: dict[str, int]) -> None:
    res = client.post(
        f"/api/v1/campaigns/{campaign_id}/stronghold/deposit",
        json={"gold": gold, "materials": materials},
    )
    assert res.status_code == 200, res.text


def _upgraded_event_count(mock_bus) -> int:
    entries = mock_bus.streams.get(STREAM_STRONGHOLD, [])
    return sum(
        "runefoble.events.downtime.stronghold_upgraded" in entry[1].get("event_type", "")
        for entry in entries
    )


def test_deposit_adds_gold_and_materials_to_the_treasury(session_client: TestClient, mock_bus):
    """A deposit through the public route funds the treasury and the material store."""
    camp_id = create_owned_campaign(session_client)

    res = session_client.post(
        f"/api/v1/campaigns/{camp_id}/stronghold/deposit",
        json={"gold": 500, "materials": {"wood": 40}},
    )

    assert res.status_code == 200, res.text
    assert res.json()["treasury_gold"] == 500
    assert res.json()["stored_materials"] == {"wood": 40}
    entries = mock_bus.streams.get(STREAM_STRONGHOLD, [])
    assert any(
        "runefoble.events.downtime.stronghold_deposited" in entry[1].get("event_type", "")
        for entry in entries
    )


def test_upgrade_charges_exact_tier_cost_from_the_table(session_client: TestClient, mock_bus):
    """An upgrade with an empty body charges the tier 1 cost of the facility, and no more."""
    camp_id = create_owned_campaign(session_client)
    _deposit(session_client, camp_id, gold=500, materials={"wood": 40})

    res = session_client.post(
        f"/api/v1/campaigns/{camp_id}/stronghold/upgrade",
        json={"facility_id": "watchtower"},
    )

    assert res.status_code == 200, res.text
    assert res.json()["gold_spent"] == 100
    assert res.json()["materials_spent"] == {"wood": 20}
    state = session_client.get(f"/api/v1/campaigns/{camp_id}/stronghold").json()
    assert state["treasury_gold"] == 400
    assert state["stored_materials"]["wood"] == 20
    assert state["facilities"]["watchtower"] == 1
    assert _upgraded_event_count(mock_bus) == 1


def test_upgrade_naming_gold_spent_is_refused_with_no_event(session_client: TestClient, mock_bus):
    """A client-set gold cost answers 422. The treasury and the facility do not change."""
    camp_id = create_owned_campaign(session_client)
    _deposit(session_client, camp_id, gold=500, materials={"wood": 40})

    res = session_client.post(
        f"/api/v1/campaigns/{camp_id}/stronghold/upgrade",
        json={"facility_id": "watchtower", "gold_spent": 1},
    )

    assert res.status_code == 422, res.text
    state = session_client.get(f"/api/v1/campaigns/{camp_id}/stronghold").json()
    assert state["treasury_gold"] == 500
    assert state["facilities"]["watchtower"] == 0
    assert _upgraded_event_count(mock_bus) == 0


def test_upgrade_naming_materials_spent_is_refused_with_no_event(
    session_client: TestClient, mock_bus
):
    """A client-set material cost answers 422. The material store does not change."""
    camp_id = create_owned_campaign(session_client)
    _deposit(session_client, camp_id, gold=500, materials={"wood": 40})

    res = session_client.post(
        f"/api/v1/campaigns/{camp_id}/stronghold/upgrade",
        json={"facility_id": "watchtower", "materials_spent": {"wood": 0}},
    )

    assert res.status_code == 422, res.text
    state = session_client.get(f"/api/v1/campaigns/{camp_id}/stronghold").json()
    assert state["stored_materials"]["wood"] == 40
    assert state["facilities"]["watchtower"] == 0
    assert _upgraded_event_count(mock_bus) == 0


def test_upgrade_refused_on_gold_shortfall_records_nothing(session_client: TestClient, mock_bus):
    """A tier cost that exceeds the treasury is refused with 409 and no event."""
    camp_id = create_owned_campaign(session_client)
    _deposit(session_client, camp_id, gold=50, materials={"wood": 20})

    res = session_client.post(
        f"/api/v1/campaigns/{camp_id}/stronghold/upgrade",
        json={"facility_id": "watchtower"},
    )

    assert res.status_code == 409, res.text
    assert "gold" in res.json()["detail"].lower()
    state = session_client.get(f"/api/v1/campaigns/{camp_id}/stronghold").json()
    assert state["treasury_gold"] == 50
    assert state["stored_materials"]["wood"] == 20
    assert state["facilities"]["watchtower"] == 0
    assert _upgraded_event_count(mock_bus) == 0


def test_upgrade_refused_on_material_shortfall_records_nothing(
    session_client: TestClient, mock_bus
):
    """A tier material cost that exceeds the store is refused with 409 and no event."""
    camp_id = create_owned_campaign(session_client)
    _deposit(session_client, camp_id, gold=500, materials={"wood": 5})

    res = session_client.post(
        f"/api/v1/campaigns/{camp_id}/stronghold/upgrade",
        json={"facility_id": "watchtower"},
    )

    assert res.status_code == 409, res.text
    assert "wood" in res.json()["detail"].lower()
    state = session_client.get(f"/api/v1/campaigns/{camp_id}/stronghold").json()
    assert state["treasury_gold"] == 500
    assert state["stored_materials"]["wood"] == 5
    assert state["facilities"]["watchtower"] == 0
    assert _upgraded_event_count(mock_bus) == 0


def test_upgrade_refused_when_material_is_missing_entirely(session_client: TestClient, mock_bus):
    """A tier material that the store never held counts as a shortfall."""
    camp_id = create_owned_campaign(session_client)
    _deposit(session_client, camp_id, gold=500, materials={})

    res = session_client.post(
        f"/api/v1/campaigns/{camp_id}/stronghold/upgrade",
        json={"facility_id": "watchtower"},
    )

    assert res.status_code == 409, res.text
    assert _upgraded_event_count(mock_bus) == 0


def test_empty_deposit_is_refused_and_records_nothing(session_client: TestClient, mock_bus):
    """A deposit that adds no gold and no material is a client error with no event."""
    camp_id = create_owned_campaign(session_client)

    res = session_client.post(
        f"/api/v1/campaigns/{camp_id}/stronghold/deposit",
        json={"gold": 0, "materials": {}},
    )

    assert res.status_code == 400, res.text
    entries = mock_bus.streams.get(STREAM_STRONGHOLD, [])
    assert not any(
        "runefoble.events.downtime.stronghold_deposited" in entry[1].get("event_type", "")
        for entry in entries
    )
    state = session_client.get(f"/api/v1/campaigns/{camp_id}/stronghold").json()
    assert state["treasury_gold"] == 0


def test_negative_deposit_is_refused_and_records_nothing(session_client: TestClient, mock_bus):
    """A negative material amount must not reduce the store through a deposit."""
    camp_id = create_owned_campaign(session_client)
    _deposit(session_client, camp_id, gold=500, materials={"wood": 5})

    res = session_client.post(
        f"/api/v1/campaigns/{camp_id}/stronghold/deposit",
        json={"gold": 0, "materials": {"wood": -50}},
    )

    assert res.status_code == 400, res.text
    state = session_client.get(f"/api/v1/campaigns/{camp_id}/stronghold").json()
    assert state["stored_materials"]["wood"] == 5
    assert state["treasury_gold"] == 500
    assert _upgraded_event_count(mock_bus) == 0


def test_player_cannot_deposit_resources(session_client: TestClient, mock_bus):
    """A deposit creates gold, so a joined player is refused with 403 and nothing is recorded."""
    camp_id = create_owned_campaign(session_client)
    invite = session_client.post(f"/api/v1/campaigns/{camp_id}/invites", json={"role": "player"})
    assert invite.status_code == 201, invite.text
    player = {"Authorization": f"Bearer {SIGNING_ISSUER.mint('user-treasury-player')}"}
    joined = session_client.post(
        "/api/v1/campaigns/join", json={"invite_token": invite.json()["token"]}, headers=player
    )
    assert joined.status_code == 200, joined.text

    res = session_client.post(
        f"/api/v1/campaigns/{camp_id}/stronghold/deposit",
        json={"gold": 9999, "materials": {}},
        headers=player,
    )

    assert res.status_code == 403, res.text
    entries = mock_bus.streams.get(STREAM_STRONGHOLD, [])
    assert not any(
        "runefoble.events.downtime.stronghold_deposited" in entry[1].get("event_type", "")
        for entry in entries
    )
