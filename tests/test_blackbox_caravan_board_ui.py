"""Blackbox TDD frontdoor test suite for Cross-Campaign Caravan Trading & Frontier Bounty Board UI.

Part of TASK-0136 / PRD-0007 / US-0058.
Governed by:
- ADR-0001: SpiceDB Zanzibar Object-Level Authorization
- ADR-0006: Redis Streams Event Bus
- ADR-0013: Microfrontend Architecture and Service Component Vendoring
- Hard Invariant 1: Object-level authorization runs through SpiceDB Zanzibar schema
- Hard Invariant 2: Domain state transitions powered by eventsource-py
- Hard Invariant 6: File length limit (< 500 lines)
- Hard Invariant 7: Blackbox TDD with frontdoor setup (zero backdoor state manipulation)
"""

from __future__ import annotations

import json
from pathlib import Path
from uuid import uuid4

import pytest
from fastapi.testclient import TestClient
from game_session.dependencies import (
    STREAM_WEST_MARCHES,
    set_event_bus,
    set_spicedb_client,
)
from game_session.main import app as session_app
from runefoble_auth.spicedb import MockSpiceDBClient
from runefoble_platform.mock_redis import MockAsyncRedis
from runefoble_platform.redis_bus import RedisStreamsEventBus

REPO_ROOT = Path(__file__).resolve().parent.parent


@pytest.fixture
def mock_bus():
    redis_client = MockAsyncRedis()
    bus = RedisStreamsEventBus(client=redis_client)
    set_event_bus(bus)
    yield redis_client
    set_event_bus(None)


@pytest.fixture
def spicedb_client() -> MockSpiceDBClient:
    mock_spicedb = MockSpiceDBClient()
    set_spicedb_client(mock_spicedb)
    return mock_spicedb


@pytest.fixture
def client(spicedb_client: MockSpiceDBClient) -> TestClient:
    return TestClient(session_app)


# ---------------------------------------------------------------------------
# 1. Microfrontend Manifest & Package Structure Integrity
# ---------------------------------------------------------------------------


def test_caravan_board_ui_manifest_frontdoor(client: TestClient) -> None:
    """Verify game_session service advertises runefoble-caravan-board via GET /ui/manifest."""
    response = client.get("/ui/manifest")
    assert response.status_code == 200
    data = response.json()
    assert data["service"] == "game_session"
    assert data["package"] == "@runefoble/game-session-ui"
    assert data["version"] == "0.1.0"
    assert "runefoble-caravan-board" in data["components"]

    # Also test the routed alias /game_session/ui/manifest
    alias_res = client.get("/game_session/ui/manifest")
    assert alias_res.status_code == 200
    assert "runefoble-caravan-board" in alias_res.json()["components"]


def test_manifest_file_matches_advertised_manifest() -> None:
    """Verify services/game_session/ui/manifest.json matches runtime advertising."""
    manifest_path = REPO_ROOT / "services/game_session/ui/manifest.json"
    assert manifest_path.is_file(), f"{manifest_path} must exist"

    manifest_data = json.loads(manifest_path.read_text(encoding="utf-8"))
    assert manifest_data["service"] == "game_session"
    assert manifest_data["package"] == "@runefoble/game-session-ui"
    assert "runefoble-caravan-board" in manifest_data["components"]


def test_caravan_board_typescript_exports_and_custom_element() -> None:
    """Verify UI package configuration, exports, and Custom Element decorators."""
    ui_dir = REPO_ROOT / "services/game_session/ui"

    pkg_json = json.loads((ui_dir / "package.json").read_text(encoding="utf-8"))
    assert pkg_json["name"] == "@runefoble/game-session-ui"
    assert "./runefoble-caravan-board" in pkg_json["exports"]
    assert "./runefoble-caravan-board.styles" in pkg_json["exports"]

    assert (ui_dir / "tsconfig.json").is_file()
    assert (ui_dir / "src/index.ts").is_file()
    index_content = (ui_dir / "src/index.ts").read_text(encoding="utf-8")
    assert "runefoble-caravan-board" in index_content

    styles_file = ui_dir / "src/runefoble-caravan-board.styles.ts"
    assert styles_file.is_file()
    assert "caravanBoardStyles" in styles_file.read_text(encoding="utf-8")

    comp_file = ui_dir / "src/runefoble-caravan-board.ts"
    assert comp_file.is_file()
    comp_src = comp_file.read_text(encoding="utf-8")
    assert "@customElement('runefoble-caravan-board')" in comp_src
    assert "class RunefobleCaravanBoard" in comp_src


def test_caravan_board_component_features() -> None:
    """Verify component implementation contains required UI features and Bauhaus tokens."""
    comp_file = REPO_ROOT / "services/game_session/ui/src/runefoble-caravan-board.ts"
    comp_src = comp_file.read_text(encoding="utf-8")

    # One-click Accept Escort Contract
    assert "Accept Escort Contract" in comp_src
    assert "acceptContract" in comp_src

    # Caravan Manifest Details Modal
    modal_file = REPO_ROOT / "services/game_session/ui/src/runefoble-caravan-modal.ts"
    assert modal_file.is_file()
    modal_src = modal_file.read_text(encoding="utf-8")

    assert "isModalOpen" in comp_src
    assert "renderCaravanManifestModal" in comp_src
    assert "Caravan Manifest:" in modal_src
    assert "Departure Settlement:" in modal_src
    assert "Destination Stronghold:" in modal_src
    assert "Cargo Inventory" in modal_src
    assert "Escort Fee Payout:" in modal_src

    # Active Transit Route Status Pill & Ambush Alerts
    assert "transit-status-pill" in comp_src
    assert "transit-progress-header" in comp_src
    assert "progress-track" in comp_src
    assert "progress-fill" in comp_src
    assert "ambush-alert-badge" in comp_src

    # Real-time notifications
    assert "notification-banner" in comp_src
    assert "notificationMessage" in comp_src

    # Bauhaus styling file check
    styles_file = REPO_ROOT / "services/game_session/ui/src/runefoble-caravan-board.styles.ts"
    styles_src = styles_file.read_text(encoding="utf-8")
    assert "--rf-border-color" in styles_src
    assert "--rf-shadow-hard" in styles_src
    assert ".transit-status-pill" in styles_src
    assert ".manifest-modal" in styles_src
    assert ".modal-backdrop" in styles_src


def test_storybook_stories_contract() -> None:
    """Verify Storybook stories simulate active caravan transit, ambush warnings, and contract payouts."""
    stories_file = REPO_ROOT / "services/game_session/ui/src/runefoble-caravan-board.stories.ts"
    assert stories_file.is_file()
    stories_code = stories_file.read_text(encoding="utf-8")
    assert "DefaultNoticeBoard" in stories_code
    assert "ActiveCaravanTransit" in stories_code
    assert "AmbushWarningAlert" in stories_code
    assert "CaravanManifestModalOpen" in stories_code
    assert "GuildOfficerManagement" in stories_code
    assert "ContractPayoutFulfilled" in stories_code


# ---------------------------------------------------------------------------
# 2. Public REST API Frontdoor Acceptance & SpiceDB Zanzibar Authorization
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_blackbox_caravan_contract_accept_and_stream_events(
    client: TestClient,
    spicedb_client: MockSpiceDBClient,
    mock_bus: MockAsyncRedis,
) -> None:
    """Verify one-click contract acceptance via public frontdoor REST endpoint and Redis Streams."""
    officer_id = "officer_karina"
    contractor_id = "party_leader_bram"
    campaign_poster = str(uuid4())
    campaign_contractor = str(uuid4())

    # 1. Establish shared world
    world_res = client.post(
        "/api/v1/shared-worlds",
        json={"name": "Frontier Marches Trading League"},
        headers={"x-user-id": officer_id},
    )
    assert world_res.status_code == 201
    world_id = world_res.json()["shared_world_id"]

    # SpiceDB authorization relationships
    await spicedb_client.write_relationship(
        "campaign", campaign_poster, "owner", "user", officer_id
    )
    await spicedb_client.write_relationship(
        "campaign", campaign_contractor, "owner", "user", contractor_id
    )
    await spicedb_client.write_relationship(
        "shared_world", world_id, "trade", "user", contractor_id
    )

    client.post(
        f"/api/v1/shared-worlds/{world_id}/campaigns",
        json={"campaign_id": campaign_poster, "party_name": "Guild Overseers"},
        headers={"x-user-id": officer_id},
    )
    client.post(
        f"/api/v1/shared-worlds/{world_id}/campaigns",
        json={"campaign_id": campaign_contractor, "party_name": "The Amber Vanguard"},
        headers={"x-user-id": officer_id},
    )

    # 2. Post contract to notice board
    post_res = client.post(
        f"/api/v1/shared-worlds/{world_id}/caravans/contracts",
        json={
            "origin_outpost": "Bastion Cross",
            "destination_outpost": "Ironford",
            "cargo": {"iron_ingots": 50, "timber": 20},
            "cargo_value": 450,
            "route_risk_level": "medium",
            "transit_stages": 2,
            "escort_collateral": 75,
            "reward_gold": 250,
            "reward_reputation": 20,
            "posted_by_campaign_id": campaign_poster,
        },
        headers={"x-user-id": officer_id},
    )
    assert post_res.status_code == 201
    contract = post_res.json()["contract"]
    contract_id = contract["contract_id"]
    assert contract["status"] == "open"

    # 3. Acceptance via public REST frontdoor (simulating button click in UI)
    accept_res = client.post(
        f"/api/v1/shared-worlds/{world_id}/caravans/contracts/{contract_id}/accept",
        json={
            "contractor_campaign_id": campaign_contractor,
            "contractor_party_name": "The Amber Vanguard",
        },
        headers={"x-user-id": contractor_id},
    )
    assert accept_res.status_code == 200
    accepted_data = accept_res.json()["contract"]
    assert accepted_data["status"] == "accepted"
    assert accepted_data["contractor_party_name"] == "The Amber Vanguard"

    # 4. Verify public notice board query returns the accepted contract
    board_res = client.get(
        f"/api/v1/shared-worlds/{world_id}/caravans/contracts",
        headers={"x-user-id": contractor_id},
    )
    assert board_res.status_code == 200
    contracts = board_res.json()["contracts"]
    matched = next((c for c in contracts if c["contract_id"] == contract_id), None)
    assert matched is not None
    assert matched["status"] == "accepted"
    assert matched["contractor_party_name"] == "The Amber Vanguard"

    # 5. Verify domain event published to Redis Streams
    entries = mock_bus.streams.get(STREAM_WEST_MARCHES, [])
    assert any("CaravanContractAccepted" in str(entry[1]) for entry in entries)
