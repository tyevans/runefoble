"""Blackbox UI contract and manifest discovery tests for Miniature Knockback Physics (TASK-0171).

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


def test_ui_manifest_frontdoor_contract(client: TestClient) -> None:
    """Verify board_state GET /ui/manifest frontdoor exposes table components."""
    resp = client.get("/ui/manifest")
    assert resp.status_code == 200, resp.text
    manifest = resp.json()

    assert manifest["service"] == "board_state"
    assert manifest["package"] == "@runefoble/board-state-ui"
    assert "runefoble-tabletop-3d" in manifest["components"]
    assert "runefoble-board" in manifest["components"]


def test_manifest_file_matches_frontdoor_endpoint(client: TestClient) -> None:
    """Verify services/board_state/ui/manifest.json matches runtime endpoint response."""
    manifest_path = REPO_ROOT / "services/board_state/ui/manifest.json"
    file_data = json.loads(manifest_path.read_text(encoding="utf-8"))
    api_data = client.get("/ui/manifest").json()

    assert file_data["service"] == api_data["service"]
    assert file_data["package"] == api_data["package"]
    assert file_data["components"] == api_data["components"]
