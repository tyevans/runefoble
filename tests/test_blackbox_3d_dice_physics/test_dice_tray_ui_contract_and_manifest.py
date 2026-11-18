"""Blackbox UI contract and manifest discovery tests for 3D Dice Tray (TASK-0170).

Governed by:
- ADR-0004: Lit Web Components and Storybook UI
- ADR-0012: Design System Theming and Accessibility Contrast Invariants
- ADR-0013: Microfrontend Architecture and Service Component Vendoring
- Hard Invariant 6: File length limit (< 500 lines)
- Hard Invariant 7: Blackbox TDD with Frontdoor Setup
"""

from __future__ import annotations

import json

from fastapi.testclient import TestClient

from .conftest import REPO_ROOT


def test_ui_manifest_advertises_dice_tray_3d(client: TestClient) -> None:
    """Verify board_state GET /ui/manifest frontdoor exposes runefoble-dice-tray-3d."""
    resp = client.get("/ui/manifest")
    assert resp.status_code == 200, resp.text
    manifest = resp.json()

    assert manifest["service"] == "board_state"
    assert manifest["package"] == "@runefoble/board-state-ui"
    assert "runefoble-dice-tray-3d" in manifest["components"]
    assert "runefoble-dice-tray-3d" in manifest["tags"]
    assert "./src/runefoble-dice-tray-3d.styles.ts" in manifest["styles"]

    # Verify routed alias /board_state/ui/manifest
    alias_resp = client.get("/board_state/ui/manifest")
    assert alias_resp.status_code == 200
    assert "runefoble-dice-tray-3d" in alias_resp.json()["components"]


def test_manifest_file_matches_frontdoor_endpoint(client: TestClient) -> None:
    """Verify services/board_state/ui/manifest.json matches runtime endpoint response."""
    manifest_path = REPO_ROOT / "services/board_state/ui/manifest.json"
    file_data = json.loads(manifest_path.read_text(encoding="utf-8"))
    api_data = client.get("/ui/manifest").json()

    assert file_data["service"] == api_data["service"]
    assert file_data["package"] == api_data["package"]
    assert "runefoble-dice-tray-3d" in file_data["components"]
    assert file_data["components"] == api_data["components"]
