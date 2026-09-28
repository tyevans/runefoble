"""Blackbox frontdoor tests for Town Bulletin Board, Civic Proclamations, and Rumor Network.

Part of TASK-0263 / PRD-0024 / US-0076.
Governed by ADR-0001 (SpiceDB Zanzibar), ADR-0002 (Domain Events via eventsource-py),
ADR-0004 (Lit Web Components), ADR-0006 (Redis Streams), and Hard Invariant 7 (Blackbox TDD).
"""

from __future__ import annotations

from pathlib import Path
from uuid import uuid4

import pytest
from fastapi.testclient import TestClient
from game_session.dependencies import (
    STREAM_WEST_MARCHES,
    set_event_bus,
    set_spicedb_client,
)
from game_session.main import app
from runefoble_auth.spicedb import MockSpiceDBClient
from runefoble_platform.mock_redis import MockAsyncRedis
from runefoble_platform.redis_bus import RedisStreamsEventBus

REPO_ROOT = Path(__file__).resolve().parent.parent


@pytest.fixture
def mock_bus() -> MockAsyncRedis:
    bus_client = MockAsyncRedis()
    set_event_bus(RedisStreamsEventBus(client=bus_client))
    yield bus_client
    set_event_bus(None)


@pytest.fixture
def spicedb() -> MockSpiceDBClient:
    db = MockSpiceDBClient()
    set_spicedb_client(db)
    yield db
    set_spicedb_client(None)


@pytest.fixture
def client(spicedb: MockSpiceDBClient, mock_bus: MockAsyncRedis) -> TestClient:
    return TestClient(app)


def assert_event_emitted(mock_bus: MockAsyncRedis, event_name: str) -> None:
    """Verify that a domain event was published to the West Marches Redis stream."""
    entries = mock_bus.streams.get(STREAM_WEST_MARCHES, [])
    ev_norm = event_name.lower().replace("_", "")
    assert any(ev_norm in str(entry[1]).lower().replace("_", "") for entry in entries), (
        f"Expected event '{event_name}' in stream '{STREAM_WEST_MARCHES}', but found: {entries}"
    )


def test_blackbox_bulletin_board_manifest_and_components(client: TestClient) -> None:
    """Verify UI manifest advertises runefoble-bulletin-board and files exist per DoD."""
    res = client.get("/ui/manifest")
    assert res.status_code == 200
    manifest = res.json()
    assert "runefoble-bulletin-board" in manifest["components"]

    component_file = REPO_ROOT / "frontend" / "src" / "components" / "runefoble-bulletin-board.ts"
    styles_file = (
        REPO_ROOT / "frontend" / "src" / "components" / "runefoble-bulletin-board.styles.ts"
    )
    modals_file = (
        REPO_ROOT / "frontend" / "src" / "components" / "runefoble-bulletin-board.modals.ts"
    )
    stories_file = (
        REPO_ROOT / "frontend" / "src" / "stories" / "runefoble-bulletin-board.stories.ts"
    )

    for f in [component_file, styles_file, modals_file, stories_file]:
        assert f.exists(), f"File {f} must exist"
        line_count = len(f.read_text().splitlines())
        assert line_count < 400, f"File {f.name} exceeds 400 lines: {line_count}"

    # TASK-0274: Modular style decomposition invariants
    assert len(styles_file.read_text().splitlines()) < 40, (
        f"Aggregator {styles_file.name} must be < 40 lines"
    )

    layout_styles_file = (
        REPO_ROOT / "frontend" / "src" / "styles" / "bulletin-board-layout.styles.ts"
    )
    card_styles_file = REPO_ROOT / "frontend" / "src" / "styles" / "bulletin-board-card.styles.ts"
    dialog_styles_file = (
        REPO_ROOT / "frontend" / "src" / "styles" / "bulletin-board-dialog.styles.ts"
    )

    for f in [layout_styles_file, card_styles_file, dialog_styles_file]:
        assert f.exists(), f"Extracted style file {f} must exist"
        count = len(f.read_text().splitlines())
        assert count < 150, f"Style sheet {f.name} must be < 150 lines: {count}"


@pytest.mark.asyncio
async def test_blackbox_pin_and_list_bulletin_notices(
    client: TestClient, spicedb: MockSpiceDBClient, mock_bus: MockAsyncRedis
) -> None:
    """Pin notices across board types and categories and query filtered lists."""
    campaign_id = str(uuid4())
    mayor_id = f"mayor_{uuid4().hex[:8]}"
    adventurer_id = f"adv_{uuid4().hex[:8]}"

    # Setup campaign authorization
    await spicedb.write_relationship("campaign", campaign_id, "player", "user", mayor_id)
    await spicedb.write_relationship("campaign", campaign_id, "player", "user", adventurer_id)

    # 1. Found settlement via HTTP POST
    found_res = client.post(
        f"/api/v1/campaigns/{campaign_id}/settlements",
        json={
            "name": "Oakhaven Haven",
            "scale": "village",
            "biome": "river_confluence",
            "coordinates": {"x": 100.0, "y": 200.0},
        },
        headers={"x-user-id": mayor_id},
    )
    assert found_res.status_code == 201, found_res.text
    sid = found_res.json()["settlement_id"]

    # 2. Pin Monster Bounty to Town Square
    bounty_payload = {
        "board_type": "town_square",
        "title": "WANTED: Manticore of Wyvern Crag",
        "category": "bounty",
        "content": "A ravenous beast preys on merchant caravans. 250gp reward.",
        "wax_sealed": False,
        "cipher_encoded": False,
    }
    bounty_res = client.post(
        f"/api/v1/settlements/{sid}/bulletin",
        json=bounty_payload,
        headers={"x-user-id": adventurer_id},
    )
    assert bounty_res.status_code == 201, bounty_res.text
    bounty_data = bounty_res.json()
    assert bounty_data["title"] == bounty_payload["title"]
    assert bounty_data["author_id"] == adventurer_id
    assert bounty_data["category"] == "bounty"
    assert_event_emitted(mock_bus, "BulletinNoticePinned")

    # 3. Pin Tavern Rumor
    rumor_payload = {
        "board_type": "tavern",
        "title": "Ghost Ship in the Reeds",
        "category": "rumor",
        "content": "Fishers whisper of green lantern lights floating over the marsh.",
        "wax_sealed": False,
        "cipher_encoded": False,
    }
    rumor_res = client.post(
        f"/api/v1/settlements/{sid}/bulletin",
        json=rumor_payload,
        headers={"x-user-id": adventurer_id},
    )
    assert rumor_res.status_code == 201

    # 4. Pin Wax-Sealed Town Council Ordinance
    ord_payload = {
        "board_type": "town_square",
        "title": "Sundown Curfew Proclamation",
        "category": "ordinance",
        "content": "By royal decree of Mayor Aldous, city gates lock at dusk.",
        "wax_sealed": True,
        "cipher_encoded": False,
    }
    ord_res = client.post(
        f"/api/v1/settlements/{sid}/bulletin",
        json=ord_payload,
        headers={"x-user-id": mayor_id},
    )
    assert ord_res.status_code == 201
    assert ord_res.json()["wax_sealed"] is True

    # 5. List all active notices
    list_all = client.get(
        f"/api/v1/settlements/{sid}/bulletin",
        headers={"x-user-id": adventurer_id},
    )
    assert list_all.status_code == 200
    all_notices = list_all.json()
    assert len(all_notices) == 3

    # 6. Filter by board_type='town_square'
    list_square = client.get(
        f"/api/v1/settlements/{sid}/bulletin?board_type=town_square",
        headers={"x-user-id": adventurer_id},
    )
    assert list_square.status_code == 200
    square_notices = list_square.json()
    assert len(square_notices) == 2
    assert all(n["board_type"] == "town_square" for n in square_notices)

    # 7. Filter by category='rumor'
    list_rumors = client.get(
        f"/api/v1/settlements/{sid}/bulletin?category=rumor",
        headers={"x-user-id": adventurer_id},
    )
    assert list_rumors.status_code == 200
    rumor_notices = list_rumors.json()
    assert len(rumor_notices) == 1
    assert rumor_notices[0]["title"] == "Ghost Ship in the Reeds"


@pytest.mark.asyncio
async def test_blackbox_cipher_notice_decryption_workflow(
    client: TestClient, spicedb: MockSpiceDBClient, mock_bus: MockAsyncRedis
) -> None:
    """Pin a cipher-encoded notice, verify masking, submit correct decryption, and unlock secret text."""
    campaign_id = str(uuid4())
    rogue_id = f"rogue_{uuid4().hex[:8]}"
    sleuth_id = f"sleuth_{uuid4().hex[:8]}"
    spectator_id = f"spectator_{uuid4().hex[:8]}"

    await spicedb.write_relationship("campaign", campaign_id, "player", "user", rogue_id)
    await spicedb.write_relationship("campaign", campaign_id, "player", "user", sleuth_id)
    await spicedb.write_relationship("campaign", campaign_id, "player", "user", spectator_id)

    found_res = client.post(
        f"/api/v1/campaigns/{campaign_id}/settlements",
        json={"name": "Shadowport Haven", "scale": "village"},
        headers={"x-user-id": rogue_id},
    )
    sid = found_res.json()["settlement_id"]

    # 1. Rogue pins a coded Thieves' Cant notice
    secret_text = "Midnight rendezvous at the Gilded Serpent back alley behind the barrels."
    cipher_payload = {
        "board_type": "tavern",
        "title": "Scrawled Cant Symbols",
        "category": "rumor",
        "content": "Seek the shadow where the three-toed crow perches.",
        "wax_sealed": False,
        "cipher_encoded": True,
        "cipher_puzzle": "rot13",
        "cipher_solution": "gilded serpent",
        "cipher_hint": "Where gold scales rattle...",
        "hidden_content": secret_text,
    }
    pin_res = client.post(
        f"/api/v1/settlements/{sid}/bulletin",
        json=cipher_payload,
        headers={"x-user-id": rogue_id},
    )
    assert pin_res.status_code == 201
    notice_id = pin_res.json()["notice_id"]

    # 2. Sleuth views bulletin: secret is masked prior to solve
    sleuth_view = client.get(
        f"/api/v1/settlements/{sid}/bulletin",
        headers={"x-user-id": sleuth_id},
    )
    assert sleuth_view.status_code == 200
    notices = sleuth_view.json()
    sleuth_notice = next(n for n in notices if n["notice_id"] == notice_id)
    assert sleuth_notice["cipher_encoded"] is True
    assert sleuth_notice["is_decrypted"] is False
    assert sleuth_notice["hidden_content"] is None

    # 3. Sleuth submits incorrect solution -> 400 Bad Request
    fail_res = client.post(
        f"/api/v1/settlements/{sid}/bulletin/{notice_id}/decrypt",
        json={"solution": "wrong answer"},
        headers={"x-user-id": sleuth_id},
    )
    assert fail_res.status_code == 400
    assert "Incorrect cipher solution" in fail_res.json()["detail"]

    # 4. Sleuth submits correct solution -> 200 OK & secret revealed
    solve_res = client.post(
        f"/api/v1/settlements/{sid}/bulletin/{notice_id}/decrypt",
        json={"solution": "gilded serpent"},
        headers={"x-user-id": sleuth_id},
    )
    assert solve_res.status_code == 200, solve_res.text
    solve_data = solve_res.json()
    assert solve_data["status"] == "decrypted"
    assert solve_data["decrypted_content"] == secret_text
    assert_event_emitted(mock_bus, "CipherNoticeDecrypted")

    # 5. Subsequent GET by Sleuth now has is_decrypted=True and reveals hidden_content
    sleuth_unlocked = client.get(
        f"/api/v1/settlements/{sid}/bulletin",
        headers={"x-user-id": sleuth_id},
    )
    unlocked_notice = next(n for n in sleuth_unlocked.json() if n["notice_id"] == notice_id)
    assert unlocked_notice["is_decrypted"] is True
    assert unlocked_notice["hidden_content"] == secret_text

    # 6. Spectator who has NOT solved it still sees hidden_content as None
    spectator_view = client.get(
        f"/api/v1/settlements/{sid}/bulletin",
        headers={"x-user-id": spectator_id},
    )
    spectator_notice = next(n for n in spectator_view.json() if n["notice_id"] == notice_id)
    assert spectator_notice["is_decrypted"] is False
    assert spectator_notice["hidden_content"] is None


@pytest.mark.asyncio
async def test_blackbox_bulletin_notice_removal_and_fulfillment(
    client: TestClient, spicedb: MockSpiceDBClient, mock_bus: MockAsyncRedis
) -> None:
    """Pin a notice and remove it, asserting removal event and disappearance from active list."""
    campaign_id = str(uuid4())
    officer_id = f"officer_{uuid4().hex[:8]}"

    await spicedb.write_relationship("campaign", campaign_id, "player", "user", officer_id)

    found_res = client.post(
        f"/api/v1/campaigns/{campaign_id}/settlements",
        json={"name": "Fortress Bastion", "scale": "village"},
        headers={"x-user-id": officer_id},
    )
    sid = found_res.json()["settlement_id"]

    pin_res = client.post(
        f"/api/v1/settlements/{sid}/bulletin",
        json={
            "board_type": "guildhall",
            "title": "Mercenary Caravan Escort",
            "category": "job",
            "content": "Guards needed for 3-day transit through Whispering Woods.",
        },
        headers={"x-user-id": officer_id},
    )
    nid = pin_res.json()["notice_id"]

    # Delete / fulfill notice
    del_res = client.delete(
        f"/api/v1/settlements/{sid}/bulletin/{nid}",
        headers={"x-user-id": officer_id},
    )
    assert del_res.status_code == 200
    del_data = del_res.json()
    assert del_data["status"] == "removed"
    assert_event_emitted(mock_bus, "BulletinNoticeRemoved")

    # Verify not in active notices
    active_res = client.get(
        f"/api/v1/settlements/{sid}/bulletin",
        headers={"x-user-id": officer_id},
    )
    assert len(active_res.json()) == 0


@pytest.mark.asyncio
async def test_blackbox_bulletin_board_zanzibar_authorization(
    client: TestClient, spicedb: MockSpiceDBClient
) -> None:
    """Verify unauthorized users are forbidden from pinning or removing notices."""
    campaign_id = str(uuid4())
    gm_id = f"gm_{uuid4().hex[:8]}"
    intruder_id = f"intruder_{uuid4().hex[:8]}"

    await spicedb.write_relationship("campaign", campaign_id, "player", "user", gm_id)

    found_res = client.post(
        f"/api/v1/campaigns/{campaign_id}/settlements",
        json={"name": "Sanctuary Keep", "scale": "village"},
        headers={"x-user-id": gm_id},
    )
    sid = found_res.json()["settlement_id"]

    # Intruder lacks permission on settlement -> 403 Forbidden
    unauth_pin = client.post(
        f"/api/v1/settlements/{sid}/bulletin",
        json={
            "board_type": "town_square",
            "title": "Fake Ordinance",
            "category": "ordinance",
            "content": "All gold belongs to bandits now.",
        },
        headers={"x-user-id": intruder_id},
    )
    assert unauth_pin.status_code == 403
    assert "Permission denied" in unauth_pin.json()["detail"]
