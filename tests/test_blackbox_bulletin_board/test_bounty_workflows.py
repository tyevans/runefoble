"""Blackbox tests for bounty workflows, notice fulfillment, and removal.

Part of TASK-0276 / PRD-0024 / US-0076. Governed by ADR-0001, ADR-0002, ADR-0008.
"""

from __future__ import annotations

from uuid import uuid4

import pytest
from fastapi.testclient import TestClient
from runefoble_auth.spicedb import MockSpiceDBClient
from runefoble_platform.mock_redis import MockAsyncRedis

from .conftest import assert_event_emitted


@pytest.mark.asyncio
async def test_blackbox_bounty_posting_and_fulfillment(
    client: TestClient, spicedb: MockSpiceDBClient, mock_bus: MockAsyncRedis
) -> None:
    """Pin monster bounty with escrow metadata, query, and fulfill notice."""
    cid, officer = str(uuid4()), f"off_{uuid4().hex[:8]}"
    await spicedb.write_relationship("campaign", cid, "player", "user", officer)

    res = client.post(
        f"/api/v1/campaigns/{cid}/settlements",
        json={"name": "Fortress Bastion", "scale": "village"},
        headers={"x-user-id": officer},
    )
    sid = res.json()["settlement_id"]

    # Pin bounty notice
    payload = {
        "board_type": "town_square",
        "title": "WANTED: Manticore",
        "category": "bounty",
        "content": "A beast preys on caravans. 250gp reward.",
        "metadata": {"reward_gp": 250, "escrow": True},
    }
    bounty_res = client.post(
        f"/api/v1/settlements/{sid}/bulletin", json=payload, headers={"x-user-id": officer}
    )
    assert bounty_res.status_code == 201
    nid = bounty_res.json()["notice_id"]
    assert bounty_res.json()["metadata"]["reward_gp"] == 250
    assert_event_emitted(mock_bus, "BulletinNoticePinned")

    # Fulfill / remove bounty notice
    del_res = client.delete(
        f"/api/v1/settlements/{sid}/bulletin/{nid}?reason=fulfilled", headers={"x-user-id": officer}
    )
    assert del_res.status_code == 200 and del_res.json()["status"] == "removed"
    assert_event_emitted(mock_bus, "BulletinNoticeRemoved")

    # Active notices should now be empty
    active = client.get(
        f"/api/v1/settlements/{sid}/bulletin", headers={"x-user-id": officer}
    ).json()
    assert len(active) == 0


@pytest.mark.asyncio
async def test_blackbox_bulletin_notice_expiration_and_removal_lifecycle(
    client: TestClient, spicedb: MockSpiceDBClient
) -> None:
    """Test notice expiration, duplicate removal error, 404 handling, and unauthorized delete."""
    cid, officer, intruder = str(uuid4()), f"off_{uuid4().hex[:8]}", f"int_{uuid4().hex[:8]}"
    await spicedb.write_relationship("campaign", cid, "player", "user", officer)

    res = client.post(
        f"/api/v1/campaigns/{cid}/settlements",
        json={"name": "Timberhold Haven", "scale": "village"},
        headers={"x-user-id": officer},
    )
    sid = res.json()["settlement_id"]

    pin = client.post(
        f"/api/v1/settlements/{sid}/bulletin",
        json={
            "board_type": "guildhall",
            "title": "Escort",
            "category": "job",
            "content": "Guards.",
        },
        headers={"x-user-id": officer},
    )
    nid = pin.json()["notice_id"]
    url = f"/api/v1/settlements/{sid}/bulletin/{nid}"

    # Unauthorized delete -> 403 Forbidden
    assert client.delete(url, headers={"x-user-id": intruder}).status_code == 403

    # Remove with expired reason -> 200
    assert client.delete(f"{url}?reason=expired", headers={"x-user-id": officer}).status_code == 200

    # Duplicate delete -> 400
    assert client.delete(url, headers={"x-user-id": officer}).status_code == 400

    # Nonexistent notice -> 404
    assert client.delete(f"{url}_missing", headers={"x-user-id": officer}).status_code == 404
