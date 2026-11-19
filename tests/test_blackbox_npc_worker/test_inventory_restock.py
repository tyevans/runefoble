"""Blackbox tests: a worker restock is an event, and worker routes sync before they publish.

Governed by ADR-0011, ADR-0015 and Hard Invariant 7 (TASK-0888). A service restart is
simulated by a new app with a new container over the same event store. The Redis double is the
process boundary. Setup and reads go through the public worker and establishment routes.
"""

from __future__ import annotations

from collections.abc import Callable
from typing import Any
from uuid import uuid4

import pytest
from fastapi.testclient import TestClient
from game_session.shared.streams import STREAM_WEST_MARCHES
from runefoble_auth.mock import MockSpiceDBClient

from tests.helpers.game_session_app import app_with_container, build_test_container
from tests.helpers.mock_redis import MockAsyncRedis
from tests.helpers.stream_events import assert_stream_events
from tests.helpers.ws_identity import SIGNING_ISSUER

pytestmark = pytest.mark.usefixtures("trusted_ws_issuer")


class UnreachableRedis(MockAsyncRedis):
    """A Redis double whose stream writes fail, as when the broker is down."""

    async def xadd(self, stream: str, fields: dict[str, Any]) -> str:
        raise ConnectionError("redis unreachable")


@pytest.fixture
def restart_service() -> Callable[[], TestClient]:
    """Return a function that starts a new app with a new container over the same event store."""

    def _restart() -> TestClient:
        return TestClient(app_with_container(build_test_container()))

    return _restart


async def _worker(
    client: TestClient, spicedb: MockSpiceDBClient
) -> tuple[dict[str, str], str, str]:
    campaign_id, dm_id = str(uuid4()), f"dm_{uuid4().hex[:8]}"
    await spicedb.write_relationship("campaign", campaign_id, "dungeon_master", "user", dm_id)
    await spicedb.write_relationship("campaign", campaign_id, "player", "user", dm_id)
    h = {"Authorization": f"Bearer {SIGNING_ISSUER.mint(dm_id)}"}
    s_res = client.post(
        f"/api/v1/campaigns/{campaign_id}/settlements",
        json={"name": "Ironhaven", "districts": ["market"]},
        headers=h,
    )
    assert s_res.status_code == 201, s_res.text
    est = client.post(
        f"/api/v1/settlements/{s_res.json()['settlement_id']}/establishments",
        json={"district_id": "market", "category": "commerce", "name": "Anvil"},
        headers=h,
    )
    assert est.status_code == 201, est.text
    eid = est.json()["establishment_id"]
    worker = client.post(
        f"/api/v1/establishments/{eid}/workers",
        json={"name": "Torvin", "role": "armorer", "mood": "content"},
        headers=h,
    )
    assert worker.status_code == 201, worker.text
    return h, eid, worker.json()["npc_id"]


@pytest.mark.asyncio
async def test_restock_survives_a_restart_and_raises_an_event(
    client: TestClient,
    spicedb: MockSpiceDBClient,
    mock_bus: MockAsyncRedis,
    restart_service: Callable[[], TestClient],
) -> None:
    """A restock is stored as an event. A restarted service still shows the added quantity."""
    h, _, npc_id = await _worker(client, spicedb)
    item = {"item_id": "rope", "name": "Hemp rope", "quantity": 3, "unit_price": 2}
    first = client.post(f"/api/v1/npcs/{npc_id}/inventory/restock", json=item, headers=h)
    assert first.status_code == 200, first.text
    again = client.post(
        f"/api/v1/npcs/{npc_id}/inventory/restock",
        json={**item, "quantity": 2, "unit_price": 4},
        headers=h,
    )
    assert again.status_code == 200 and again.json()["quantity"] == 5
    vault = client.post(
        f"/api/v1/npcs/{npc_id}/inventory/restock",
        params={"destination": "backroom"},
        json={"item_id": "poison", "quantity": 1, "is_contraband": True},
        headers=h,
    )
    assert vault.status_code == 200, vault.text
    assert_stream_events(mock_bus, "WorkerInventoryRestocked")

    client = restart_service()
    read = client.get(f"/api/v1/npcs/{npc_id}/inventory/rope", headers=h)
    assert read.status_code == 200, read.text
    assert read.json()["quantity"] == 5 and read.json()["unit_price"] == 4
    shelf = client.get(f"/api/v1/npcs/{npc_id}/inventory", headers=h).json()
    assert [i["item_id"] for i in shelf["shelf_inventory"]] == ["rope"]
    backroom = client.get(f"/api/v1/npcs/{npc_id}/inventory/vault", headers=h)
    assert [i["item_id"] for i in backroom.json()] == ["poison"]


@pytest.mark.asyncio
async def test_restock_to_an_unknown_destination_answers_422(
    client: TestClient, spicedb: MockSpiceDBClient
) -> None:
    """Only shelf and backroom are destinations. Another value is a bad request."""
    h, _, npc_id = await _worker(client, spicedb)
    res = client.post(
        f"/api/v1/npcs/{npc_id}/inventory/restock",
        params={"destination": "attic"},
        json={"item_id": "rope"},
        headers=h,
    )
    assert res.status_code == 422, res.text
    vault = client.get(f"/api/v1/npcs/{npc_id}/inventory/vault", headers=h)
    assert vault.json() == []


@pytest.mark.asyncio
async def test_mood_change_that_cannot_publish_still_updates_the_summary(
    client: TestClient, spicedb: MockSpiceDBClient, use_redis_client: Any
) -> None:
    """A mood change answers 503 when the stream is down. The establishment summary is current."""
    h, eid, npc_id = await _worker(client, spicedb)
    before = client.get(f"/api/v1/establishments/{eid}", headers=h).json()

    use_redis_client(UnreachableRedis())
    mood = client.patch(
        f"/api/v1/npcs/{npc_id}/mood", json={"mood": "hostile", "temperament": "stern"}, headers=h
    )
    assert mood.status_code == 503, mood.text

    after = client.get(f"/api/v1/establishments/{eid}", headers=h).json()
    assert after["projected_service_quality"] < before["projected_service_quality"]


@pytest.mark.asyncio
async def test_relationship_that_cannot_publish_still_updates_the_summary(
    client: TestClient, spicedb: MockSpiceDBClient, use_redis_client: Any
) -> None:
    """A rival tie answers 503 when the stream is down. The tension index is current."""
    h, eid, npc_id = await _worker(client, spicedb)
    peer = client.post(
        f"/api/v1/establishments/{eid}/workers",
        json={"name": "Marta", "role": "clerk"},
        headers=h,
    ).json()["npc_id"]
    before = client.get(f"/api/v1/establishments/{eid}", headers=h).json()

    use_redis_client(UnreachableRedis())
    tie = {"target_npc_id": peer, "relation_type": "rival", "intensity": 1.0}
    res = client.post(f"/api/v1/npcs/{npc_id}/relationships", json=tie, headers=h)
    assert res.status_code == 503, res.text

    after = client.get(f"/api/v1/establishments/{eid}", headers=h).json()
    assert after["interpersonal_tension_index"] > before["interpersonal_tension_index"]


@pytest.mark.asyncio
async def test_a_repeated_relationship_call_keeps_one_tie_and_one_event(
    client: TestClient, spicedb: MockSpiceDBClient, mock_bus: MockAsyncRedis
) -> None:
    """A retried relationship call does not add a second tie or a second event."""
    h, _, npc_id = await _worker(client, spicedb)
    tie = {"target_npc_id": "leo", "relation_type": "mentor", "intensity": 0.8}
    for _ in range(2):
        res = client.post(f"/api/v1/npcs/{npc_id}/relationships", json=tie, headers=h)
        assert res.status_code == 201, res.text
    ties = client.get(f"/api/v1/npcs/{npc_id}/relationships", headers=h).json()
    assert [(t["target_npc_id"], t["relation_type"]) for t in ties] == [("leo", "mentor")]
    entries = mock_bus.streams.get(STREAM_WEST_MARCHES, [])
    formed = [f for _, f in entries if "npc_relationship_formed" in str(f)]
    assert len(formed) == 1
