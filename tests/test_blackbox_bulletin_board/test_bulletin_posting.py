"""Blackbox tests for bulletin board posting, querying, and component manifest.

Part of TASK-0276 / PRD-0024 / US-0076. Governed by ADR-0001, ADR-0004, ADR-0008.
"""

from __future__ import annotations

from uuid import uuid4

import pytest
from fastapi.testclient import TestClient
from runefoble_auth.spicedb import MockSpiceDBClient

from tests.helpers.mock_redis import MockAsyncRedis
from tests.helpers.ws_identity import SIGNING_ISSUER

from .conftest import assert_event_emitted


def test_blackbox_bulletin_board_manifest_and_components(client: TestClient) -> None:
    """Verify UI manifest advertises runefoble-bulletin-board."""
    res = client.get("/ui/manifest")
    assert res.status_code == 200 and "runefoble-bulletin-board" in res.json()["components"]


@pytest.mark.asyncio
async def test_blackbox_pin_and_list_bulletin_notices(
    client: TestClient, spicedb: MockSpiceDBClient, mock_bus: MockAsyncRedis
) -> None:
    """Pin notices across board types and categories and query filtered lists."""
    cid, mayor, adv = str(uuid4()), f"m_{uuid4().hex[:8]}", f"a_{uuid4().hex[:8]}"
    for uid in (mayor, adv):
        await spicedb.write_relationship("campaign", cid, "player", "user", uid)

    res = client.post(
        f"/api/v1/campaigns/{cid}/settlements",
        json={"name": "Oakhaven Haven", "scale": "village"},
        headers={"Authorization": f"Bearer {SIGNING_ISSUER.mint(mayor)}"},
    )
    sid = res.json()["settlement_id"]
    base_url = f"/api/v1/settlements/{sid}/bulletin"

    # Pin Rumor to Tavern and Ordinance to Town Square
    rumor = {"board_type": "tavern", "title": "Ghost", "category": "rumor", "content": "Lights."}
    ordinance = {
        "board_type": "town_square",
        "title": "Curfew",
        "category": "ordinance",
        "content": "Lock.",
    }
    client.post(
        base_url, json=rumor, headers={"Authorization": f"Bearer {SIGNING_ISSUER.mint(adv)}"}
    )
    ord_res = client.post(
        base_url, json=ordinance, headers={"Authorization": f"Bearer {SIGNING_ISSUER.mint(mayor)}"}
    )
    assert ord_res.status_code == 201
    assert_event_emitted(mock_bus, "BulletinNoticePinned")

    # List all and filter by board_type and category
    all_notices = client.get(
        base_url, headers={"Authorization": f"Bearer {SIGNING_ISSUER.mint(adv)}"}
    ).json()
    assert len(all_notices) == 2

    square = client.get(
        f"{base_url}?board_type=town_square",
        headers={"Authorization": f"Bearer {SIGNING_ISSUER.mint(adv)}"},
    ).json()
    assert len(square) == 1 and square[0]["category"] == "ordinance"

    rumors = client.get(
        f"{base_url}?category=rumor",
        headers={"Authorization": f"Bearer {SIGNING_ISSUER.mint(adv)}"},
    ).json()
    assert len(rumors) == 1 and rumors[0]["title"] == "Ghost"


@pytest.mark.asyncio
async def test_blackbox_bulletin_posting_zanzibar_authorization(
    client: TestClient, spicedb: MockSpiceDBClient
) -> None:
    """Verify unauthorized users are forbidden from pinning notices."""
    cid, gm, intruder = str(uuid4()), f"gm_{uuid4().hex[:8]}", f"int_{uuid4().hex[:8]}"
    await spicedb.write_relationship("campaign", cid, "player", "user", gm)

    res = client.post(
        f"/api/v1/campaigns/{cid}/settlements",
        json={"name": "Sanctuary Keep", "scale": "village"},
        headers={"Authorization": f"Bearer {SIGNING_ISSUER.mint(gm)}"},
    )
    sid = res.json()["settlement_id"]

    fake = {
        "board_type": "town_square",
        "title": "Fake",
        "category": "ordinance",
        "content": "Theft.",
    }
    unauth = client.post(
        f"/api/v1/settlements/{sid}/bulletin",
        json=fake,
        headers={"Authorization": f"Bearer {SIGNING_ISSUER.mint(intruder)}"},
    )
    assert unauth.status_code == 403
    assert "Permission denied" in unauth.json()["detail"]
