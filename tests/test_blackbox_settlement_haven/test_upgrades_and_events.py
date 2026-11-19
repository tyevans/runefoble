"""Blackbox tests for settlement and establishment upgrades and event publishing.

Governed by ADR-0001, ADR-0002, ADR-0007, and Hard Invariant 7.
"""

from __future__ import annotations

from uuid import uuid4

import pytest
from fastapi.testclient import TestClient
from runefoble_events.events import (
    EstablishmentConstructedEvent,
    EstablishmentUpgradedEvent,
    SettlementFoundedEvent,
    SettlementTierUpgradedEvent,
)

from tests.helpers.campaign_setup import create_campaign, invite_and_join
from tests.helpers.mock_redis import MockAsyncRedis
from tests.helpers.stream_events import assert_stream_events
from tests.helpers.ws_identity import SIGNING_ISSUER

pytestmark = pytest.mark.usefixtures("trusted_ws_issuer")


def test_settlement_tier_upgrade_and_events(client: TestClient, mock_bus: MockAsyncRedis) -> None:
    """Verify settlement tier upgrades, prosperity validation, and domain events."""
    uid = f"mayor_{uuid4().hex[:8]}"
    h = {"Authorization": f"Bearer {SIGNING_ISSUER.mint(uid)}"}
    cid = create_campaign(client, uid)

    b = {"name": "Pine", "scale": "hamlet", "prosperity": 50, "districts": ["commons"]}
    res = client.post(f"/api/v1/campaigns/{cid}/settlements", json=b, headers=h)
    assert res.status_code == 201
    sid = res.json()["settlement_id"]
    assert_stream_events(mock_bus, "SettlementFounded")

    found_ce = SettlementFoundedEvent(
        settlement_id=sid, campaign_id=cid, name="Pine", scale="hamlet", biome="forest"
    ).to_cloudevent_dict()
    assert found_ce["specversion"] == "1.0" and "settlement_founded" in found_ce["type"]

    upg_url = f"/api/v1/settlements/{sid}/upgrade-tier"
    # Prosperity gate failure (50 < 100)
    fail_res = client.post(upg_url, json={"new_tier": 2, "prosperity": 50}, headers=h)
    assert fail_res.status_code == 400
    assert "Insufficient civic prosperity" in fail_res.json()["detail"]

    # Prosperity gate pass (150 >= 100)
    upg_res = client.post(upg_url, json={"new_tier": 2, "prosperity": 150}, headers=h)
    assert upg_res.status_code == 200
    upg_data = upg_res.json()
    assert upg_data["tier"] == 2 and upg_data["scale"] == "village"
    assert_stream_events(mock_bus, "SettlementTierUpgraded")

    tier_ce = SettlementTierUpgradedEvent(
        settlement_id=sid, old_tier=1, new_tier=2
    ).to_cloudevent_dict()
    assert tier_ce["specversion"] == "1.0" and "settlement_tier_upgraded" in tier_ce["type"]


def test_establishment_upgrade_and_events(client: TestClient, mock_bus: MockAsyncRedis) -> None:
    """Verify establishment upgrades, amenity modifications, and domain events."""
    owner_id, uid = f"owner_{uuid4().hex[:8]}", f"innkeeper_{uuid4().hex[:8]}"
    h = {"Authorization": f"Bearer {SIGNING_ISSUER.mint(uid)}"}
    cid = create_campaign(client, owner_id)
    invite_and_join(client, cid, owner_id, uid, "player")

    s_body = {"name": "River", "scale": "village", "districts": ["commons", "trading_post"]}
    s_res = client.post(f"/api/v1/campaigns/{cid}/settlements", json=s_body, headers=h)
    sid = s_res.json()["settlement_id"]

    est_res = client.post(
        f"/api/v1/settlements/{sid}/establishments",
        json={"district_id": "trading_post", "category": "hospitality", "name": "Inn"},
        headers=h,
    )
    assert est_res.status_code == 201
    eid = est_res.json()["establishment_id"]
    assert_stream_events(mock_bus, "EstablishmentConstructed")

    est_ce = EstablishmentConstructedEvent(
        establishment_id=eid,
        settlement_id=sid,
        district_id="trading_post",
        category="hospitality",
        name="Inn",
    ).to_cloudevent_dict()
    assert est_ce["specversion"] == "1.0" and "establishment_constructed" in est_ce["type"]

    upg_res = client.post(
        f"/api/v1/establishments/{eid}/upgrade",
        json={"tier": 2, "added_amenities": ["billiards_table"], "capacity": 50},
        headers=h,
    )
    assert upg_res.status_code == 200
    assert upg_res.json()["tier"] == 2 and "billiards_table" in upg_res.json()["amenities"]
    assert_stream_events(mock_bus, "EstablishmentUpgraded")

    upg_ce = EstablishmentUpgradedEvent(
        establishment_id=eid, settlement_id=sid, tier=2
    ).to_cloudevent_dict()
    assert upg_ce["specversion"] == "1.0" and "establishment_upgraded" in upg_ce["type"]
