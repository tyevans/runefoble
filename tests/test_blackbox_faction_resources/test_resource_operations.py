"""Tests for faction resource adjustments, treasury queries, and Zanzibar authorization.

Governed by ADR-0003, ADR-0007, ADR-0011, and Hard Invariant 7 (Blackbox TDD).
"""

from __future__ import annotations

from uuid import uuid4

import pytest
from eventsource.domain.event_registry import get_event_class_or_none
from fastapi.testclient import TestClient
from runefoble_events.events import (
    FactionBriberyAttemptedEvent,
    FactionMercenaryRecruitedEvent,
    FactionResourceUpdatedEvent,
)
from runefoble_platform.event_sourcing import create_aggregate_repository
from the_watcher.dependencies import get_faction_resource_repo, set_faction_resource_repo
from the_watcher.factions.resources.aggregate import FactionResourceAggregate

from tests.helpers.event_store_seam import OutageEventStore
from tests.helpers.module_state import restored_seam
from tests.helpers.ws_identity import SIGNING_ISSUER

from .conftest import setup_campaign_roles

pytestmark = pytest.mark.usefixtures("trusted_ws_issuer")


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
        f"/api/v1/factions/{fid}/resources/adjust",
        json={"treasury_delta": 100, "campaign_id": camp_id},
        headers={"Authorization": f"Bearer {SIGNING_ISSUER.mint(player_user)}"},
    )
    assert res.status_code == 403 and "Forbidden" in res.json()["detail"]

    view_res = client.get(
        f"/api/v1/factions/{fid}/resources?campaign_id={camp_id}",
        headers={"Authorization": f"Bearer {SIGNING_ISSUER.mint(player_user)}"},
    )
    assert view_res.status_code == 200

    dm_res = client.post(
        f"/api/v1/factions/{fid}/resources/adjust",
        json={"treasury_delta": 200, "campaign_id": camp_id},
        headers={"Authorization": f"Bearer {SIGNING_ISSUER.mint(dm_user)}"},
    )
    assert dm_res.status_code == 200 and dm_res.json()["treasury"] == 300


@pytest.mark.asyncio
async def test_frontdoor_resource_adjust_deplete_and_query(client: TestClient):
    """Verify frontdoor API adjusts treasury, contraband, and bounds values at zero."""
    camp_id, dm_user, _ = await setup_campaign_roles()
    fid = f"fact-{uuid4().hex[:8]}"

    # Deposit treasury and contraband
    res = client.post(
        f"/api/v1/factions/{fid}/resources/adjust",
        json={"treasury_delta": 250, "contraband_delta": 15, "campaign_id": camp_id},
        headers={"Authorization": f"Bearer {SIGNING_ISSUER.mint(dm_user)}"},
    )
    assert res.status_code == 200 and res.json()["treasury"] == 350
    assert res.json()["contraband_score"] == 15

    # Query via GET
    get_res = client.get(
        f"/api/v1/factions/{fid}/resources?campaign_id={camp_id}",
        headers={"Authorization": f"Bearer {SIGNING_ISSUER.mint(dm_user)}"},
    )
    assert get_res.status_code == 200 and get_res.json()["treasury"] == 350

    # Deplete 50 gold
    spend = client.post(
        f"/api/v1/factions/{fid}/resources/adjust",
        json={"treasury_delta": -50, "campaign_id": camp_id},
        headers={"Authorization": f"Bearer {SIGNING_ISSUER.mint(dm_user)}"},
    )
    assert spend.status_code == 200 and spend.json()["treasury"] == 300

    # Capacity bounds: excessive deduction floors at zero
    drain = client.post(
        f"/api/v1/factions/{fid}/resources/adjust",
        json={"treasury_delta": -500, "campaign_id": camp_id},
        headers={"Authorization": f"Bearer {SIGNING_ISSUER.mint(dm_user)}"},
    )
    assert drain.status_code == 200 and drain.json()["treasury"] == 0


def test_faction_resource_adjust_answers_503_on_store_outage(client: TestClient) -> None:
    """A store outage on the faction resource load answers 503. No empty faction replaces it.

    The faction repository gets its own store, which fails every read.
    """
    with restored_seam(
        get_faction_resource_repo,
        set_faction_resource_repo,
        create_aggregate_repository(FactionResourceAggregate, event_store=OutageEventStore()),
        replace=True,
    ):
        resp = client.post(
            f"/api/v1/factions/fact-{uuid4().hex[:8]}/resources/adjust",
            json={"treasury_delta": 100, "campaign_id": str(uuid4())},
        )
    assert resp.status_code == 503, resp.text
