"""Microfrontend manifest and component delivery tests for West Marches UI (TASK-0176).

Governed by:
- ADR-0003: UV Monorepo Workspace for Python BCs
- ADR-0013: Microfrontend Architecture and Service Component Vendoring
- Hard Invariant 6: File length limit (< 500 lines, target < 100 lines)
- Hard Invariant 7: Blackbox TDD with Frontdoor Setup
"""

from __future__ import annotations

import json

from fastapi.testclient import TestClient

from .conftest import REPO_ROOT


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
    data = json.loads(manifest_path.read_text(encoding="utf-8"))
    assert data["service"] == "campaign_lore"
    assert data["package"] == "@runefoble/campaign-lore-ui"
    assert "runefoble-west-marches-atlas" in data["components"]


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
    assert "runefoble-west-marches-atlas" in (ui_dir / "src/index.ts").read_text(encoding="utf-8")
    assert "westMarchesAtlasStyles" in (
        ui_dir / "src/runefoble-west-marches-atlas.styles.ts"
    ).read_text(encoding="utf-8")
    comp_src = (ui_dir / "src/runefoble-west-marches-atlas.ts").read_text(encoding="utf-8")
    assert "@customElement('runefoble-west-marches-atlas')" in comp_src
    assert "class RunefobleWestMarchesAtlas" in comp_src


def test_storybook_stories_contract() -> None:
    """Verify Storybook stories provide interactive multi-party and stronghold scenarios."""
    stories_code = (
        REPO_ROOT / "services/campaign_lore/ui/src/runefoble-west-marches-atlas.stories.ts"
    ).read_text(encoding="utf-8")
    expected = (
        "DefaultFrontierView",
        "CommunalStrongholdView",
        "TavernNoticeBoardView",
        "RestrictedPlayerView",
        "GuildOfficerAdminView",
    )
    for story in expected:
        assert story in stories_code


def test_west_marches_decomposed_subcomponents_integrity() -> None:
    """Verify TASK-0152 decomposed sub-components, custom elements, and line limits."""
    wm = REPO_ROOT / "services/campaign_lore/ui/src/west_marches"
    assert wm.is_dir()
    for f in (
        "discovery_pin_layer.ts",
        "pin_layer.ts",
        "stronghold_dashboard_panel.ts",
        "stronghold_panel.ts",
        "frontier_hex_overlay.ts",
        "hex_overlay.ts",
    ):
        assert (wm / f).is_file(), f"{f} must exist"
    assert "@customElement('runefoble-discovery-pin-layer')" in (
        wm / "discovery_pin_layer.ts"
    ).read_text(encoding="utf-8")
    assert "@customElement('runefoble-stronghold-dashboard-panel')" in (
        wm / "stronghold_dashboard_panel.ts"
    ).read_text(encoding="utf-8")
    hex_src = (wm / "frontier_hex_overlay.ts").read_text(encoding="utf-8")
    assert (
        "@customElement('runefoble-frontier-hex-overlay')" in hex_src and "snapToHexGrid" in hex_src
    )
    for s in ("map.styles.ts", "pin.styles.ts", "stronghold.styles.ts"):
        assert len((wm / "styles" / s).read_text(encoding="utf-8").splitlines()) < 110
    atlas_src = (
        REPO_ROOT / "services/campaign_lore/ui/src/runefoble-west-marches-atlas.ts"
    ).read_text(encoding="utf-8")
    assert len(atlas_src.splitlines()) < 120
    for mod in (
        "discovery_pin_layer.ts",
        "stronghold_dashboard_panel.ts",
        "frontier_hex_overlay.ts",
    ):
        assert len((wm / mod).read_text(encoding="utf-8").splitlines()) < 150


def test_storybook_sublayer_stories_contract() -> None:
    """Verify Storybook stories contain decomposed sub-layer states."""
    code = (
        REPO_ROOT / "services/campaign_lore/ui/src/runefoble-west-marches-atlas.stories.ts"
    ).read_text(encoding="utf-8")
    for s in (
        "DiscoveryPinLayerSubView",
        "FrontierHexOverlaySubView",
        "StrongholdDashboardPanelSubView",
    ):
        assert s in code
