"""Blackbox tests for stronghold treasury funding, upgrade spending, and shortfall refusal (TASK-0774).

Setup and assertions use public HTTP routes only. Governed by ADR-0011 (the command decides,
the `@handles` method applies the recorded change) and Hard Invariant 7.
"""

from __future__ import annotations

from fastapi.testclient import TestClient
from game_session.events import STREAM_STRONGHOLD


def _owned_campaign(client: TestClient) -> str:
    """Create a campaign through the public route. The caller becomes its owner."""
    created = client.post("/api/v1/campaigns", json={"title": "Treasury Campaign"})
    assert created.status_code == 201, created.text
    return created.json()["id"]


def _deposit(client: TestClient, campaign_id: str, gold: int, materials: dict[str, int]) -> None:
    res = client.post(
        f"/api/v1/campaigns/{campaign_id}/stronghold/deposit",
        json={"gold": gold, "materials": materials},
    )
    assert res.status_code == 200, res.text


def _upgraded_event_count(mock_bus) -> int:
    entries = mock_bus.streams.get(STREAM_STRONGHOLD, [])
    return sum("StrongholdUpgraded" in entry[1].get("event_type", "") for entry in entries)


def test_deposit_adds_gold_and_materials_to_the_treasury(session_client: TestClient, mock_bus):
    """A deposit through the public route funds the treasury and the material store."""
    camp_id = _owned_campaign(session_client)

    res = session_client.post(
        f"/api/v1/campaigns/{camp_id}/stronghold/deposit",
        json={"gold": 500, "materials": {"wood": 40}},
    )

    assert res.status_code == 200, res.text
    assert res.json()["treasury_gold"] == 500
    assert res.json()["stored_materials"] == {"wood": 40}
    entries = mock_bus.streams.get(STREAM_STRONGHOLD, [])
    assert any("StrongholdDeposited" in entry[1].get("event_type", "") for entry in entries)


def test_upgrade_spends_gold_and_materials_from_the_stores(session_client: TestClient, mock_bus):
    """An affordable upgrade reduces the treasury and the material store."""
    camp_id = _owned_campaign(session_client)
    _deposit(session_client, camp_id, gold=500, materials={"wood": 40})

    res = session_client.post(
        f"/api/v1/campaigns/{camp_id}/stronghold/upgrade",
        json={"facility_id": "watchtower", "gold_spent": 200, "materials_spent": {"wood": 20}},
    )

    assert res.status_code == 200, res.text
    state = session_client.get(f"/api/v1/campaigns/{camp_id}/stronghold").json()
    assert state["treasury_gold"] == 300
    assert state["stored_materials"]["wood"] == 20
    assert state["facilities"]["watchtower"] == 1
    assert _upgraded_event_count(mock_bus) == 1


def test_upgrade_refused_on_gold_shortfall_records_nothing(session_client: TestClient, mock_bus):
    """An upgrade that costs more gold than the treasury holds is refused with no event."""
    camp_id = _owned_campaign(session_client)
    _deposit(session_client, camp_id, gold=100, materials={"wood": 20})

    res = session_client.post(
        f"/api/v1/campaigns/{camp_id}/stronghold/upgrade",
        json={"facility_id": "watchtower", "gold_spent": 200, "materials_spent": {"wood": 20}},
    )

    assert res.status_code == 409, res.text
    assert "gold" in res.json()["detail"].lower()
    state = session_client.get(f"/api/v1/campaigns/{camp_id}/stronghold").json()
    assert state["treasury_gold"] == 100
    assert state["stored_materials"]["wood"] == 20
    assert state["facilities"]["watchtower"] == 0
    assert _upgraded_event_count(mock_bus) == 0


def test_upgrade_refused_on_material_shortfall_records_nothing(
    session_client: TestClient, mock_bus
):
    """An upgrade that needs more material than the store holds is refused with no event."""
    camp_id = _owned_campaign(session_client)
    _deposit(session_client, camp_id, gold=500, materials={"wood": 5})

    res = session_client.post(
        f"/api/v1/campaigns/{camp_id}/stronghold/upgrade",
        json={"facility_id": "watchtower", "gold_spent": 100, "materials_spent": {"wood": 20}},
    )

    assert res.status_code == 409, res.text
    assert "wood" in res.json()["detail"].lower()
    state = session_client.get(f"/api/v1/campaigns/{camp_id}/stronghold").json()
    assert state["treasury_gold"] == 500
    assert state["stored_materials"]["wood"] == 5
    assert state["facilities"]["watchtower"] == 0
    assert _upgraded_event_count(mock_bus) == 0


def test_upgrade_refused_when_material_is_missing_entirely(session_client: TestClient, mock_bus):
    """A material that the store never held counts as a shortfall."""
    camp_id = _owned_campaign(session_client)
    _deposit(session_client, camp_id, gold=500, materials={})

    res = session_client.post(
        f"/api/v1/campaigns/{camp_id}/stronghold/upgrade",
        json={"facility_id": "watchtower", "gold_spent": 100, "materials_spent": {"wood": 20}},
    )

    assert res.status_code == 409, res.text
    assert _upgraded_event_count(mock_bus) == 0


def test_empty_deposit_is_refused_and_records_nothing(session_client: TestClient, mock_bus):
    """A deposit that adds no gold and no material is a client error with no event."""
    camp_id = _owned_campaign(session_client)

    res = session_client.post(
        f"/api/v1/campaigns/{camp_id}/stronghold/deposit",
        json={"gold": 0, "materials": {}},
    )

    assert res.status_code == 400, res.text
    entries = mock_bus.streams.get(STREAM_STRONGHOLD, [])
    assert not any("StrongholdDeposited" in entry[1].get("event_type", "") for entry in entries)
    state = session_client.get(f"/api/v1/campaigns/{camp_id}/stronghold").json()
    assert state["treasury_gold"] == 0


def test_negative_material_spend_is_refused_and_records_nothing(
    session_client: TestClient, mock_bus
):
    """A negative material amount must not add to the store. The route answers 400, no event."""
    camp_id = _owned_campaign(session_client)
    _deposit(session_client, camp_id, gold=500, materials={"wood": 5})

    res = session_client.post(
        f"/api/v1/campaigns/{camp_id}/stronghold/upgrade",
        json={"facility_id": "watchtower", "gold_spent": 100, "materials_spent": {"wood": -50}},
    )

    assert res.status_code == 400, res.text
    state = session_client.get(f"/api/v1/campaigns/{camp_id}/stronghold").json()
    assert state["stored_materials"]["wood"] == 5
    assert state["treasury_gold"] == 500
    assert _upgraded_event_count(mock_bus) == 0
