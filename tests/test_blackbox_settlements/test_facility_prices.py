"""Blackbox tests for settlement facility prices and the haven treasury (TASK-0786).

A facility upgrade spends the tier price from the haven treasury. A shortfall answers 409
and records no event. The treasury is funded through the public deposit route.

Governed by ADR-0001, ADR-0011, and Hard Invariant 7 (Blackbox TDD with frontdoor setup).
"""

from __future__ import annotations

from uuid import uuid4

import pytest
from fastapi.testclient import TestClient
from game_session.events import STREAM_WEST_MARCHES
from runefoble_auth.spicedb import MockSpiceDBClient

from tests.helpers.mock_redis import MockAsyncRedis
from tests.helpers.stream_events import assert_stream_events
from tests.helpers.ws_identity import bearer

pytestmark = pytest.mark.usefixtures("trusted_ws_issuer")

FOUNDER = "builder_orla"


async def _charter_haven(client: TestClient, spicedb: MockSpiceDBClient) -> tuple[str, str]:
    """Charter a haven through the public routes. Return (settlement_id, campaign_id)."""
    camp = str(uuid4())
    world = client.post(
        "/api/v1/shared-worlds",
        json={"name": "Ashen Vale", "frontier_region": "Cinder Hills"},
        headers=bearer(FOUNDER),
    )
    world_id = world.json()["shared_world_id"]
    await spicedb.write_relationship("shared_world", world_id, "participant", "user", FOUNDER)
    await spicedb.write_relationship("campaign", camp, "player", "user", FOUNDER)
    charter = client.post(
        "/settlements",
        json={
            "name": "Cinder Hold",
            "shared_world_id": world_id,
            "founded_by_campaign_id": camp,
        },
        headers=bearer(FOUNDER),
    )
    assert charter.status_code == 201, charter.text
    return charter.json()["settlement_id"], camp


@pytest.mark.asyncio
async def test_deposit_funds_the_haven_treasury(
    client: TestClient, spicedb: MockSpiceDBClient, mock_bus: MockAsyncRedis
) -> None:
    """A founder deposits gold and materials. The read model shows the new balance."""
    sid, _ = await _charter_haven(client, spicedb)

    deposit = client.post(
        f"/settlements/{sid}/deposit",
        json={"gold": 500, "materials": {"timber": 100, "stone": 100}},
        headers=bearer(FOUNDER),
    )
    assert deposit.status_code == 200, deposit.text
    assert deposit.json()["gold_treasury"] == 500
    assert deposit.json()["materials_treasury"] == {"timber": 100, "stone": 100}

    view = client.get(f"/settlements/{sid}", headers=bearer(FOUNDER))
    assert view.json()["gold_treasury"] == 500
    assert_stream_events(mock_bus, "SettlementResourcesDeposited")


@pytest.mark.asyncio
async def test_upgrade_spends_the_table_cost_from_the_treasury(
    client: TestClient, spicedb: MockSpiceDBClient, mock_bus: MockAsyncRedis
) -> None:
    """A workshop upgrade to tier 2 costs 100 gold and 20 timber from the price table."""
    sid, camp = await _charter_haven(client, spicedb)
    client.post(
        f"/settlements/{sid}/deposit",
        json={"gold": 500, "materials": {"timber": 100}},
        headers=bearer(FOUNDER),
    )

    upgrade = client.post(
        f"/settlements/{sid}/upgrade",
        json={"facility_id": "workshop", "contributing_campaign_id": camp},
        headers=bearer(FOUNDER),
    )
    assert upgrade.status_code == 200, upgrade.text
    data = upgrade.json()
    assert data["facilities"]["workshop"] == 2
    assert data["gold_treasury"] == 400
    assert data["materials_treasury"] == {"timber": 80}
    assert data["gold_invested"] == 100
    assert_stream_events(mock_bus, "SettlementUpgraded")


@pytest.mark.asyncio
async def test_upgrade_shortfall_answers_409_and_records_no_event(
    client: TestClient, spicedb: MockSpiceDBClient, mock_bus: MockAsyncRedis
) -> None:
    """An unfunded haven cannot upgrade. The facility, the balance, and the stream stay put."""
    sid, camp = await _charter_haven(client, spicedb)
    client.post(
        f"/settlements/{sid}/deposit",
        json={"gold": 50, "materials": {"timber": 100}},
        headers=bearer(FOUNDER),
    )
    events_before = len(mock_bus.streams.get(STREAM_WEST_MARCHES, []))

    refused = client.post(
        f"/settlements/{sid}/upgrade",
        json={"facility_id": "workshop", "contributing_campaign_id": camp},
        headers=bearer(FOUNDER),
    )
    assert refused.status_code == 409, refused.text
    assert "gold" in refused.json()["detail"]

    assert len(mock_bus.streams.get(STREAM_WEST_MARCHES, [])) == events_before
    view = client.get(f"/settlements/{sid}", headers=bearer(FOUNDER)).json()
    assert view["facilities"]["workshop"] == 1
    assert view["gold_treasury"] == 50
    assert view["materials_treasury"] == {"timber": 100}
