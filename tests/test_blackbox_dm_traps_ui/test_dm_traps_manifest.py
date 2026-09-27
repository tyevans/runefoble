"""Manifest and microfrontend component delivery tests for DM Traps UI (TASK-0159).

Governed by:
- ADR-0004: Lit Web Components and Storybook UI
- ADR-0012: Theming System and Accessibility Contrast Invariants
- ADR-0013: Microfrontend Architecture and Service Component Vendoring
- Hard Invariant 6: File length limit (< 500 lines)
- Hard Invariant 7: Blackbox TDD with Frontdoor Setup
"""

from __future__ import annotations

import json
from uuid import uuid4

import pytest
from fastapi.testclient import TestClient
from runefoble_auth.spicedb import MockSpiceDBClient

from .conftest import REPO_ROOT


def test_dm_traps_manifest_endpoint(client: TestClient) -> None:
    """Verify GET /ui/manifest frontdoor exposes dm trap controls and map switcher."""
    resp = client.get("/ui/manifest")
    assert resp.status_code == 200
    data = resp.json()
    assert data["service"] == "board_state"
    assert data["package"] == "@runefoble/board-state-ui"
    assert data["version"] == "0.1.0"
    assert "runefoble-dm-trap-controls" in data["components"]
    assert "runefoble-map-switcher" in data["components"]
    assert "runefoble-dm-trap-controls" in data["tags"]
    assert "runefoble-map-switcher" in data["tags"]
    assert any("runefoble-dm-trap-controls.styles" in s for s in data["styles"])
    assert any("index.ts" in s for s in data["scripts"])

    # Test routed alias /board_state/ui/manifest
    alias_resp = client.get("/board_state/ui/manifest")
    assert alias_resp.status_code == 200
    alias_data = alias_resp.json()
    assert "runefoble-dm-trap-controls" in alias_data["components"]
    assert "runefoble-map-switcher" in alias_data["components"]


def test_manifest_file_matches_advertised_manifest(client: TestClient) -> None:
    """Verify services/board_state/ui/manifest.json matches runtime advertising."""
    manifest_path = REPO_ROOT / "services/board_state/ui/manifest.json"
    assert manifest_path.is_file(), f"{manifest_path} must exist"
    manifest_data = json.loads(manifest_path.read_text(encoding="utf-8"))
    endpoint_data = client.get("/ui/manifest").json()
    for field in ("service", "package", "version", "components", "tags", "styles", "scripts"):
        assert manifest_data[field] == endpoint_data[field]


def test_typescript_element_source_and_custom_elements() -> None:
    """Verify UI package configuration, exports, and Custom Element decorators."""
    ui_dir = REPO_ROOT / "services/board_state/ui"
    pkg_json = json.loads((ui_dir / "package.json").read_text(encoding="utf-8"))
    assert pkg_json["name"] == "@runefoble/board-state-ui"
    assert "./runefoble-dm-trap-controls" in pkg_json["exports"]
    assert "./runefoble-dm-trap-controls.styles" in pkg_json["exports"]
    assert "./runefoble-map-switcher" in pkg_json["exports"]

    index_src = (ui_dir / "src/index.ts").read_text(encoding="utf-8")
    assert "runefoble-dm-trap-controls" in index_src
    assert "runefoble-map-switcher" in index_src

    # DM trap controls component inspection
    trap_src = (ui_dir / "src/runefoble-dm-trap-controls.ts").read_text(encoding="utf-8")
    assert "@customElement('runefoble-dm-trap-controls')" in trap_src
    assert "class RunefobleDmTrapControls" in trap_src
    for term in (
        "selectedTrapType",
        "triggerType",
        "proximityRadius",
        "damageDice",
        "dcDetection",
        "isSecret",
        "trap-selected",
        "trap-armed",
        "trap-placed",
        "layer-toggled",
        "open-map-switcher",
        "danger-zone-preview",
    ):
        assert term in trap_src

    # Map switcher component inspection
    switcher_src = (ui_dir / "src/runefoble-map-switcher.ts").read_text(encoding="utf-8")
    assert "@customElement('runefoble-map-switcher')" in switcher_src
    assert "class RunefobleMapSwitcher" in switcher_src
    for term in (
        "currentMapId",
        "tokenTeleports",
        "map-switched",
        "switcher-closed",
        "switchMap",
        "teleport-btn",
    ):
        assert term in switcher_src

    # DM trap controls styles inspection
    styles_src = (ui_dir / "src/runefoble-dm-trap-controls.styles.ts").read_text(encoding="utf-8")
    for token in (
        "--rf-border-color",
        "--rf-accent-primary",
        "--rf-bg-surface",
        "--rf-shadow",
        "danger-zone-preview",
        "danger-pulse",
    ):
        assert token in styles_src


def test_storybook_stories_definition() -> None:
    """Verify Storybook stories include layer toggling, trap arming, danger zone and map switcher."""
    stories_file = REPO_ROOT / "services/board_state/ui/src/runefoble-dm-trap-controls.stories.ts"
    assert stories_file.is_file()
    content = stories_file.read_text(encoding="utf-8")
    expected_stories = (
        "HiddenLayerActive",
        "HiddenLayerDisabled",
        "TrapArmingPalette",
        "DangerZonePreview",
        "MultiMapSwitcherModal",
    )
    for story in expected_stories:
        assert story in content


def test_frontend_app_shell_forwarding_export() -> None:
    """Verify frontend/src/components/ re-exports the microfrontends per ADR-0013."""
    trap_forwarding = REPO_ROOT / "frontend/src/components/runefoble-dm-trap-controls.ts"
    assert trap_forwarding.is_file()
    assert "@runefoble/board-state-ui" in trap_forwarding.read_text(encoding="utf-8")

    switcher_forwarding = REPO_ROOT / "frontend/src/components/runefoble-map-switcher.ts"
    assert switcher_forwarding.is_file()
    assert "@runefoble/board-state-ui" in switcher_forwarding.read_text(encoding="utf-8")

    shell_index = REPO_ROOT / "frontend/src/index.ts"
    shell_content = shell_index.read_text(encoding="utf-8")
    assert "runefoble-dm-trap-controls" in shell_content
    assert "runefoble-map-switcher" in shell_content


def test_dm_traps_files_strictly_under_line_limits() -> None:
    """Verify all DM traps and map switcher UI files strictly comply with line limits (Hard Invariant 6)."""
    ui_dir = REPO_ROOT / "services/board_state/ui/src"
    files = [
        (ui_dir / "runefoble-dm-trap-controls.ts", 140),
        (ui_dir / "runefoble-map-switcher.ts", 140),
        (ui_dir / "runefoble-dm-trap-controls.styles.ts", 110),
        (ui_dir / "runefoble-dm-trap-controls.stories.ts", 130),
    ]
    for path, max_lines in files:
        assert path.is_file(), f"{path} must exist"
        lines = len(path.read_text(encoding="utf-8").splitlines())
        assert lines < max_lines, f"{path.name} has {lines} lines, exceeding limit of {max_lines}"


@pytest.mark.asyncio
async def test_frontdoor_contract_integration(
    client: TestClient, spicedb_client: MockSpiceDBClient
) -> None:
    """Verify UI action payloads conform with backend board API frontdoors."""
    board_id = f"board-{uuid4().hex[:8]}"
    campaign_id = f"camp-{uuid4().hex[:8]}"
    dm_user = f"dm-{uuid4().hex[:6]}"

    await spicedb_client.write_relationship(
        "campaign", campaign_id, "dungeon_master", "user", dm_user
    )
    await spicedb_client.write_relationship("board", board_id, "campaign", "campaign", campaign_id)

    # 1. Initialize board
    init_res = client.post("/api/v1/boards", json={"board_id": board_id, "cols": 15, "rows": 15})
    assert init_res.status_code == 200

    # 2. Place trap using parameters defined in UI trap preset
    trap_res = client.post(
        f"/api/v1/boards/{board_id}/traps?campaign_id={campaign_id}",
        json={
            "name": "Spike Pit",
            "x": 3,
            "y": 3,
            "trigger_type": "step",
            "proximity_radius": 1,
            "damage_dice": "2d10",
            "dc_detection": 15,
            "is_secret": True,
        },
        headers={"X-User-Id": dm_user},
    )
    assert trap_res.status_code == 201
    trap_data = trap_res.json()
    assert trap_data["name"] == "Spike Pit"
    assert trap_data["trigger_type"] == "step"

    # 3. Execute map switch using parameters defined in UI map switcher
    switch_res = client.post(
        f"/api/v1/boards/{board_id}/switch-map?campaign_id={campaign_id}",
        json={
            "new_map_id": "dungeon_lvl2",
            "cols": 20,
            "rows": 20,
            "background_image_url": "https://assets.runefoble.com/maps/dungeon_lvl2.png",
            "token_teleports": {"valeros": [10, 15]},
        },
        headers={"X-User-Id": dm_user},
    )
    assert switch_res.status_code == 200
    switch_data = switch_res.json()
    assert switch_data["new_map_id"] == "dungeon_lvl2"
    assert switch_data["cols"] == 20
    assert switch_data["rows"] == 20
