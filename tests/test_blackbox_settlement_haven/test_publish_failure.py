"""Blackbox tests: haven and worker routes answer 503 when the stream is unreachable.

Governed by ADR-0011, ADR-0015 and Hard Invariant 7 (TASK-0886). The Redis double is the
process boundary. Setup and reads go through the public haven and worker routes.
"""

from __future__ import annotations

from typing import Any
from uuid import uuid4

import pytest
from fastapi.testclient import TestClient

from tests.helpers.campaign_setup import create_campaign
from tests.helpers.mock_redis import MockAsyncRedis
from tests.helpers.ws_identity import SIGNING_ISSUER

pytestmark = pytest.mark.usefixtures("trusted_ws_issuer")


class UnreachableRedis(MockAsyncRedis):
    """A Redis double whose stream writes fail, as when the broker is down."""

    async def xadd(self, stream: str, fields: dict[str, Any]) -> str:
        raise ConnectionError("redis unreachable")


def _headers(uid: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {SIGNING_ISSUER.mint(uid)}"}


def _haven_with_worker(client: TestClient, h: dict[str, str], cid: str) -> tuple[str, str, str]:
    body = {"name": "Pine", "scale": "hamlet", "prosperity": 50, "districts": ["commons"]}
    res = client.post(f"/api/v1/campaigns/{cid}/settlements", json=body, headers=h)
    assert res.status_code == 201, res.text
    sid = res.json()["settlement_id"]
    est = client.post(
        f"/api/v1/settlements/{sid}/establishments",
        json={"district_id": "commons", "category": "hospitality", "name": "The Pine Cone"},
        headers=h,
    )
    assert est.status_code == 201, est.text
    eid = est.json()["establishment_id"]
    worker = client.post(
        f"/api/v1/establishments/{eid}/workers",
        json={"name": "Marta", "role": "barkeep", "wage": 3},
        headers=h,
    )
    assert worker.status_code == 201, worker.text
    return sid, eid, worker.json()["npc_id"]


def test_haven_and_worker_updates_answer_503_and_keep_the_saved_state(
    client: TestClient, use_redis_client: Any
) -> None:
    """Upgrades and a mood change that cannot publish answer 503. The saved state stays visible."""
    uid = f"mayor_{uuid4().hex[:8]}"
    h = _headers(uid)
    cid = create_campaign(client, uid)
    sid, eid, npc_id = _haven_with_worker(client, h, cid)

    use_redis_client(UnreachableRedis())

    tier = client.post(
        f"/api/v1/settlements/{sid}/upgrade-tier",
        json={"new_tier": 2, "prosperity": 150},
        headers=h,
    )
    assert tier.status_code == 503, tier.text
    haven = client.get(f"/api/v1/campaigns/{cid}/settlements/{sid}", headers=h)
    assert haven.status_code == 200 and haven.json()["tier"] == 2

    upgrade = client.post(
        f"/api/v1/establishments/{eid}/upgrade", json={"tier": 2, "capacity": 40}, headers=h
    )
    assert upgrade.status_code == 503, upgrade.text
    est = client.get(f"/api/v1/establishments/{eid}", headers=h)
    assert est.status_code == 200 and est.json()["tier"] == 2

    mood = client.patch(
        f"/api/v1/npcs/{npc_id}/mood", json={"mood": "grumpy", "temperament": "stern"}, headers=h
    )
    assert mood.status_code == 503, mood.text
    npc = client.get(f"/api/v1/npcs/{npc_id}", headers=h)
    assert npc.status_code == 200 and npc.json()["mood"] == "grumpy"


def test_founding_that_cannot_publish_answers_503_and_the_haven_stays_readable(
    client: TestClient, use_redis_client: Any
) -> None:
    """A founder can read a haven whose founding event failed to publish."""
    uid = f"mayor_{uuid4().hex[:8]}"
    h = _headers(uid)
    cid = create_campaign(client, uid)

    use_redis_client(UnreachableRedis())
    body = {"name": "Ash", "scale": "hamlet", "districts": ["commons"]}
    res = client.post(f"/api/v1/campaigns/{cid}/settlements", json=body, headers=h)
    assert res.status_code == 503, res.text

    listing = client.get(f"/api/v1/campaigns/{cid}/settlements", headers=h)
    assert listing.status_code == 200
    assert [s["name"] for s in listing.json()] == ["Ash"]
