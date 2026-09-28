"""Blackbox tests for bulletin board posting, querying, and component manifest.

Part of TASK-0276 / PRD-0024 / US-0076. Governed by ADR-0001, ADR-0004, ADR-0008.
"""

from __future__ import annotations

from pathlib import Path
from uuid import uuid4

import pytest
from fastapi.testclient import TestClient
from runefoble_auth.spicedb import MockSpiceDBClient
from runefoble_platform.mock_redis import MockAsyncRedis

from .conftest import assert_event_emitted

REPO_ROOT = Path(__file__).resolve().parents[2]


def test_blackbox_bulletin_board_manifest_and_components(client: TestClient) -> None:
    """Verify UI manifest advertises runefoble-bulletin-board and component files exist."""
    res = client.get("/ui/manifest")
    assert res.status_code == 200 and "runefoble-bulletin-board" in res.json()["components"]

    fe = REPO_ROOT / "frontend" / "src"
    checks = [
        (fe / "components" / "runefoble-bulletin-board.ts", 400),
        (fe / "components" / "runefoble-bulletin-board.styles.ts", 40),
        (fe / "components" / "runefoble-bulletin-board.modals.ts", 400),
        (fe / "stories" / "runefoble-bulletin-board.stories.ts", 400),
        (fe / "styles" / "bulletin-board-layout.styles.ts", 150),
        (fe / "styles" / "bulletin-board-card.styles.ts", 150),
        (fe / "styles" / "bulletin-board-dialog.styles.ts", 150),
    ]
    for path, max_lines in checks:
        assert path.exists(), f"File {path.name} must exist"
        assert len(path.read_text().splitlines()) < max_lines


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
        headers={"x-user-id": mayor},
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
    client.post(base_url, json=rumor, headers={"x-user-id": adv})
    ord_res = client.post(base_url, json=ordinance, headers={"x-user-id": mayor})
    assert ord_res.status_code == 201
    assert_event_emitted(mock_bus, "BulletinNoticePinned")

    # List all and filter by board_type and category
    all_notices = client.get(base_url, headers={"x-user-id": adv}).json()
    assert len(all_notices) == 2

    square = client.get(f"{base_url}?board_type=town_square", headers={"x-user-id": adv}).json()
    assert len(square) == 1 and square[0]["category"] == "ordinance"

    rumors = client.get(f"{base_url}?category=rumor", headers={"x-user-id": adv}).json()
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
        headers={"x-user-id": gm},
    )
    sid = res.json()["settlement_id"]

    fake = {
        "board_type": "town_square",
        "title": "Fake",
        "category": "ordinance",
        "content": "Theft.",
    }
    unauth = client.post(
        f"/api/v1/settlements/{sid}/bulletin", json=fake, headers={"x-user-id": intruder}
    )
    assert unauth.status_code == 403
    assert "Permission denied" in unauth.json()["detail"]
