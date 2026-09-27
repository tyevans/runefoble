"""Blackbox TDD frontdoor test suite for West Marches Shared Atlas & Stronghold UI Microfrontend.

Part of TASK-0135 / PRD-0007 / PRD-0014 / US-0050 / US-0058.
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
from campaign_lore.dependencies import (
    set_spicedb_client,
    set_west_marches_repo,
)
from campaign_lore.main import app as lore_app
from campaign_lore.west_marches_aggregate import WestMarchesAtlasAggregate
from fastapi.testclient import TestClient
from runefoble_auth.spicedb import MockSpiceDBClient
from runefoble_platform.event_sourcing import create_aggregate_repository

REPO_ROOT = Path(__file__).resolve().parent.parent


@pytest.fixture
def spicedb_client() -> MockSpiceDBClient:
    mock_spicedb = MockSpiceDBClient()
    set_spicedb_client(mock_spicedb)
    return mock_spicedb


@pytest.fixture
def client(spicedb_client: MockSpiceDBClient) -> TestClient:
    fresh_repo = create_aggregate_repository(WestMarchesAtlasAggregate)
    set_west_marches_repo(fresh_repo)
    return TestClient(lore_app)


# ---------------------------------------------------------------------------
# 1. Microfrontend Manifest & Package Structure Integrity
# ---------------------------------------------------------------------------


def test_west_marches_ui_manifest_frontdoor(client: TestClient) -> None:
    """Verify campaign_lore service advertises runefoble-west-marches-atlas via GET /ui/manifest."""
    response = client.get("/ui/manifest")
    assert response.status_code == 200
    data = response.json()
    assert data["service"] == "campaign_lore"
    assert data["package"] == "@runefoble/campaign-lore-ui"
    assert data["version"] == "0.1.0"
    assert "runefoble-west-marches-atlas" in data["components"]
    assert "runefoble-campaign-atlas" in data["components"]


def test_manifest_file_matches_advertised_manifest() -> None:
    """Verify services/campaign_lore/ui/manifest.json matches runtime advertising."""
    manifest_path = REPO_ROOT / "services/campaign_lore/ui/manifest.json"
    assert manifest_path.is_file(), f"{manifest_path} must exist"

    manifest_data = json.loads(manifest_path.read_text(encoding="utf-8"))
    assert manifest_data["service"] == "campaign_lore"
    assert manifest_data["package"] == "@runefoble/campaign-lore-ui"
    assert "runefoble-west-marches-atlas" in manifest_data["components"]


def test_typescript_elements_source_and_custom_elements() -> None:
    """Verify UI package configuration, exports, and Custom Element decorators."""
    ui_dir = REPO_ROOT / "services/campaign_lore/ui"

    pkg_json = json.loads((ui_dir / "package.json").read_text(encoding="utf-8"))
    assert pkg_json["name"] == "@runefoble/campaign-lore-ui"
    assert pkg_json["exports"]["."].endswith("index.ts")
    assert "./runefoble-west-marches-atlas" in pkg_json["exports"]
    assert "./runefoble-west-marches-atlas.styles" in pkg_json["exports"]

    assert (ui_dir / "tsconfig.json").is_file()
    assert (ui_dir / "src/index.ts").is_file()
    index_content = (ui_dir / "src/index.ts").read_text(encoding="utf-8")
    assert "runefoble-west-marches-atlas" in index_content

    styles_file = ui_dir / "src/runefoble-west-marches-atlas.styles.ts"
    assert styles_file.is_file()
    assert "westMarchesAtlasStyles" in styles_file.read_text(encoding="utf-8")

    comp_file = ui_dir / "src/runefoble-west-marches-atlas.ts"
    assert comp_file.is_file()
    comp_src = comp_file.read_text(encoding="utf-8")
    assert "@customElement('runefoble-west-marches-atlas')" in comp_src
    assert "class RunefobleWestMarchesAtlas" in comp_src


def test_storybook_stories_contract() -> None:
    """Verify Storybook stories provide interactive multi-party and stronghold scenarios."""
    stories_file = (
        REPO_ROOT / "services/campaign_lore/ui/src/runefoble-west-marches-atlas.stories.ts"
    )
    assert stories_file.is_file()
    stories_code = stories_file.read_text(encoding="utf-8")
    assert "DefaultFrontierView" in stories_code
    assert "CommunalStrongholdView" in stories_code
    assert "TavernNoticeBoardView" in stories_code
    assert "RestrictedPlayerView" in stories_code
    assert "GuildOfficerAdminView" in stories_code


# ---------------------------------------------------------------------------
# 2. Public REST API Frontdoor & SpiceDB Zanzibar Authorization
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_blackbox_west_marches_overview_and_zanzibar_access(
    client: TestClient,
    spicedb_client: MockSpiceDBClient,
) -> None:
    """Verify GET /api/v1/campaigns/{id}/west-marches enforces SpiceDB Zanzibar permissions."""
    campaign_id = str(uuid4())
    player_id = "rowan_ranger"
    outsider_id = "unauthorized_wanderer"

    # 1. Unauthorized outsider is rejected (HTTP 403)
    unauth_resp = client.get(
        f"/api/v1/campaigns/{campaign_id}/west-marches",
        headers={"x-user-id": outsider_id},
    )
    assert unauth_resp.status_code == 403

    # 2. Grant player view permission in SpiceDB Zanzibar
    await spicedb_client.write_relationship(
        resource_type="campaign",
        resource_id=campaign_id,
        relation="player",
        subject_type="user",
        subject_id=player_id,
    )

    # 3. Authorized player receives communal frontier state
    auth_resp = client.get(
        f"/api/v1/campaigns/{campaign_id}/west-marches",
        headers={"x-user-id": player_id},
    )
    assert auth_resp.status_code == 200
    data = auth_resp.json()
    assert data["campaign_id"] == campaign_id
    assert "outposts" in data
    assert len(data["outposts"]) >= 1


@pytest.mark.asyncio
async def test_blackbox_discovery_pins_and_popover_data(
    client: TestClient,
    spicedb_client: MockSpiceDBClient,
) -> None:
    """Verify placing milestone discovery pins and retrieving popover metadata."""
    campaign_id = str(uuid4())
    player_id = "blue_explorer"

    await spicedb_client.write_relationship(
        resource_type="campaign",
        resource_id=campaign_id,
        relation="player",
        subject_type="user",
        subject_id=player_id,
    )

    # 1. Record milestone discovery: "Sunken Crypt of Arnor"
    discovery_payload = {
        "name": "Sunken Crypt of Arnor",
        "discovery_type": "dungeon",
        "coordinates": {"x": 280.0, "y": 320.0},
        "discovered_by_party_name": "Party Blue",
        "description": "Flooded ancient crypt guarded by water elementals.",
        "danger_level": 4,
        "metadata": {"entrance": "submerged_tunnel", "biome": "fenland"},
    }
    disc_resp = client.post(
        f"/api/v1/campaigns/{campaign_id}/west-marches/discoveries",
        json=discovery_payload,
        headers={"x-user-id": player_id},
    )
    assert disc_resp.status_code == 201
    disc_data = disc_resp.json()["discovery"]
    assert disc_data["name"] == "Sunken Crypt of Arnor"
    assert disc_data["danger_level"] == 4
    assert disc_data["discovered_by_party_name"] == "Party Blue"

    # 2. Query overview and verify pin appears in discoveries list
    overview = client.get(
        f"/api/v1/campaigns/{campaign_id}/west-marches",
        headers={"x-user-id": player_id},
    ).json()
    assert len(overview["discoveries"]) == 1
    assert overview["discoveries"][0]["name"] == "Sunken Crypt of Arnor"

    # 3. Query filtered by type
    filtered = client.get(
        f"/api/v1/campaigns/{campaign_id}/west-marches?discovery_type=dungeon",
        headers={"x-user-id": player_id},
    ).json()
    assert len(filtered["discoveries"]) == 1

    empty_filter = client.get(
        f"/api/v1/campaigns/{campaign_id}/west-marches?discovery_type=outpost",
        headers={"x-user-id": player_id},
    ).json()
    assert len(empty_filter["discoveries"]) == 0


@pytest.mark.asyncio
async def test_blackbox_communal_stronghold_upgrade_and_boons(
    client: TestClient,
    spicedb_client: MockSpiceDBClient,
) -> None:
    """Verify upgrading communal stronghold facility recalculates shared boons and defense buffers."""
    campaign_id = str(uuid4())
    player_id = "alchemist_bryan"

    await spicedb_client.write_relationship(
        resource_type="campaign",
        resource_id=campaign_id,
        relation="player",
        subject_type="user",
        subject_id=player_id,
    )

    # 1. Upgrade Alchemical Workshop from Lv 1 to Lv 2
    upgrade_payload = {
        "facility_id": "alchemical_workshop",
        "gold_spent": 100,
        "materials_spent": {"timber": 20, "glass": 5},
    }
    upgrade_resp = client.post(
        f"/api/v1/campaigns/{campaign_id}/west-marches/stronghold/upgrade",
        json=upgrade_payload,
        headers={"x-user-id": player_id},
    )
    assert upgrade_resp.status_code == 200
    res = upgrade_resp.json()
    assert res["status"] == "upgraded"
    assert res["facility_id"] == "alchemical_workshop"
    assert res["new_tier"] == 2
    assert "Enhanced Potion Yield (+1 Potion)" in res["active_boons"]

    # 2. Upgrade Watchtower from Lv 1 to Lv 2 and check defensive buffer
    watch_resp = client.post(
        f"/api/v1/campaigns/{campaign_id}/west-marches/stronghold/upgrade",
        json={"facility_id": "watchtower", "gold_spent": 150},
        headers={"x-user-id": player_id},
    )
    assert watch_resp.status_code == 200
    assert watch_resp.json()["new_tier"] == 2
    assert watch_resp.json()["defensive_buffer"] >= 25


@pytest.mark.asyncio
async def test_blackbox_tavern_notice_board(
    client: TestClient,
    spicedb_client: MockSpiceDBClient,
) -> None:
    """Verify posting and reading communal tavern notice board bounties and rumors."""
    campaign_id = str(uuid4())
    player_id = "ranger_laura"

    await spicedb_client.write_relationship(
        resource_type="campaign",
        resource_id=campaign_id,
        relation="player",
        subject_type="user",
        subject_id=player_id,
    )

    # 1. Post bounty notice
    notice_payload = {
        "author_name": "Ranger Laura",
        "title": "Bounty: Cull the Marsh Trolls",
        "content": "Four marsh trolls sighted harassing supply convoys east of the Old Bridge.",
        "notice_type": "bounty",
        "bounty_reward": 150,
    }
    post_resp = client.post(
        f"/api/v1/campaigns/{campaign_id}/west-marches/tavern-board/notices",
        json=notice_payload,
        headers={"x-user-id": player_id},
    )
    assert post_resp.status_code == 201
    notice = post_resp.json()["notice"]
    assert notice["title"] == "Bounty: Cull the Marsh Trolls"
    assert notice["bounty_reward"] == 150

    # 2. Retrieve overview and verify notice is listed
    overview = client.get(
        f"/api/v1/campaigns/{campaign_id}/west-marches",
        headers={"x-user-id": player_id},
    ).json()
    assert len(overview["tavern_board"]) == 1
    assert overview["tavern_board"][0]["author_name"] == "Ranger Laura"


# ---------------------------------------------------------------------------
# 3. TASK-0152: Modular Sub-components & File Length Invariant Verification
# ---------------------------------------------------------------------------


def test_west_marches_decomposed_subcomponents_integrity() -> None:
    """Verify TASK-0152 decomposed sub-components, custom elements, and line limits."""
    wm_dir = REPO_ROOT / "services/campaign_lore/ui/src/west_marches"
    assert wm_dir.is_dir()

    # 1. Verify existence of sub-components and aliases
    pin_layer = wm_dir / "discovery_pin_layer.ts"
    pin_alias = wm_dir / "pin_layer.ts"
    stronghold_panel = wm_dir / "stronghold_dashboard_panel.ts"
    stronghold_alias = wm_dir / "stronghold_panel.ts"
    hex_overlay = wm_dir / "frontier_hex_overlay.ts"
    hex_alias = wm_dir / "hex_overlay.ts"

    for file_path in (
        pin_layer,
        pin_alias,
        stronghold_panel,
        stronghold_alias,
        hex_overlay,
        hex_alias,
    ):
        assert file_path.is_file(), f"{file_path} must exist"

    # 2. Verify Custom Element registrations
    pin_src = pin_layer.read_text(encoding="utf-8")
    assert "@customElement('runefoble-discovery-pin-layer')" in pin_src
    assert "class RunefobleDiscoveryPinLayer" in pin_src

    stronghold_src = stronghold_panel.read_text(encoding="utf-8")
    assert "@customElement('runefoble-stronghold-dashboard-panel')" in stronghold_src
    assert "class RunefobleStrongholdDashboardPanel" in stronghold_src

    hex_src = hex_overlay.read_text(encoding="utf-8")
    assert "@customElement('runefoble-frontier-hex-overlay')" in hex_src
    assert "class RunefobleFrontierHexOverlay" in hex_src
    assert "snapToHexGrid" in hex_src

    # 3. Verify styles decomposition
    styles_dir = wm_dir / "styles"
    for style_name in ("map.styles.ts", "pin.styles.ts", "stronghold.styles.ts"):
        style_path = styles_dir / style_name
        assert style_path.is_file(), f"{style_path} must exist"
        lines = len(style_path.read_text(encoding="utf-8").splitlines())
        assert lines < 110, f"{style_name} has {lines} lines (must be < 110)"

    # 4. Verify file length invariants (< 150 lines for modules, < 120 lines for atlas root)
    atlas_root = REPO_ROOT / "services/campaign_lore/ui/src/runefoble-west-marches-atlas.ts"
    atlas_lines = len(atlas_root.read_text(encoding="utf-8").splitlines())
    assert atlas_lines < 120, (
        f"runefoble-west-marches-atlas.ts has {atlas_lines} lines (must be < 120)"
    )

    for mod in (pin_layer, stronghold_panel, hex_overlay):
        mod_lines = len(mod.read_text(encoding="utf-8").splitlines())
        assert mod_lines < 150, f"{mod.name} has {mod_lines} lines (must be < 150)"


def test_storybook_sublayer_stories_contract() -> None:
    """Verify Storybook stories contain decomposed sub-layer states."""
    stories_file = (
        REPO_ROOT / "services/campaign_lore/ui/src/runefoble-west-marches-atlas.stories.ts"
    )
    stories_code = stories_file.read_text(encoding="utf-8")
    assert "DiscoveryPinLayerSubView" in stories_code
    assert "FrontierHexOverlaySubView" in stories_code
    assert "StrongholdDashboardPanelSubView" in stories_code
