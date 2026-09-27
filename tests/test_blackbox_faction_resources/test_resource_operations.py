"""Tests for faction resource adjustments, treasury queries, and Zanzibar authorization.

Governed by ADR-0003, ADR-0007, ADR-0011, and Hard Invariant 7 (Blackbox TDD).
"""

from __future__ import annotations

from uuid import uuid4

import pytest
from eventsource.domain.event_registry import get_event_class_or_none
from fastapi.testclient import TestClient
from runefoble_events import (
    FactionBriberyAttemptedEvent,
    FactionMercenaryRecruitedEvent,
    FactionResourceUpdatedEvent,
)

from .conftest import setup_campaign_roles


def test_cloudevents_registration():
    """Verify faction resource domain events are registered and conform to CloudEvents."""
    for type_name, cls in [
        ("runefoble.events.watcher.faction_resource_updated", FactionResourceUpdatedEvent),
        ("runefoble.events.watcher.faction_mercenary_recruited", FactionMercenaryRecruitedEvent),
        ("runefoble.events.watcher.faction_bribery_attempted", FactionBriberyAttemptedEvent),
    ]:
        assert get_event_class_or_none(type_name) == cls
    ce = FactionResourceUpdatedEvent(
        faction_id="f1", campaign_id="c1", treasury=500, delta_treasury=150
    ).to_cloudevent_dict()
    assert ce["specversion"] == "1.0" and ce["data"]["treasury"] == 500


@pytest.mark.asyncio
async def test_zanzibar_faction_resource_authorization(client: TestClient):
    """Verify unauthorized users cannot adjust resources, while DMs can."""
    camp_id, dm_user, player_user = await setup_campaign_roles()
    fid = f"fact-{uuid4().hex[:8]}"

    res = client.post(
        f"/factions/{fid}/resources/adjust",
        json={"treasury_delta": 100, "campaign_id": camp_id},
        headers={"X-User-Id": player_user},
    )
    assert res.status_code == 403 and "Forbidden" in res.json()["detail"]

    view_res = client.get(
        f"/factions/{fid}/resources?campaign_id={camp_id}", headers={"X-User-Id": player_user}
    )
    assert view_res.status_code == 200

    dm_res = client.post(
        f"/factions/{fid}/resources/adjust",
        json={"treasury_delta": 200, "campaign_id": camp_id},
        headers={"X-User-Id": dm_user},
    )
    assert dm_res.status_code == 200 and dm_res.json()["treasury"] == 300


@pytest.mark.asyncio
async def test_frontdoor_resource_adjust_deplete_and_query(client: TestClient):
    """Verify frontdoor API adjusts treasury, contraband, and bounds values at zero."""
    camp_id, dm_user, _ = await setup_campaign_roles()
    fid = f"fact-{uuid4().hex[:8]}"

    # Deposit treasury and contraband
    res = client.post(
        f"/factions/{fid}/resources/adjust",
        json={"treasury_delta": 250, "contraband_delta": 15, "campaign_id": camp_id},
        headers={"X-User-Id": dm_user},
    )
    assert res.status_code == 200 and res.json()["treasury"] == 350
    assert res.json()["contraband_score"] == 15

    # Query via GET
    get_res = client.get(
        f"/factions/{fid}/resources?campaign_id={camp_id}", headers={"X-User-Id": dm_user}
    )
    assert get_res.status_code == 200 and get_res.json()["treasury"] == 350

    # Deplete 50 gold
    spend = client.post(
        f"/factions/{fid}/resources/adjust",
        json={"treasury_delta": -50, "campaign_id": camp_id},
        headers={"X-User-Id": dm_user},
    )
    assert spend.status_code == 200 and spend.json()["treasury"] == 300

    # Capacity bounds: excessive deduction floors at zero
    drain = client.post(
        f"/factions/{fid}/resources/adjust",
        json={"treasury_delta": -500, "campaign_id": camp_id},
        headers={"X-User-Id": dm_user},
    )
    assert drain.status_code == 200 and drain.json()["treasury"] == 0
