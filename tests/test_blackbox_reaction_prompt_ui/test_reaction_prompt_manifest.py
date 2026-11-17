"""Manifest and microfrontend component delivery tests for Reaction Prompt UI (TASK-0158).

Governed by:
- ADR-0004: Lit Web Components and Storybook UI
- ADR-0012: Theming System and Accessibility Contrast Invariants
- ADR-0013: Microfrontend Architecture and Service Component Vendoring
- Hard Invariant 6: File length limit (< 500 lines)
- Hard Invariant 7: Blackbox TDD with Frontdoor Setup
"""

from __future__ import annotations

import json

from fastapi.testclient import TestClient

from .conftest import REPO_ROOT


def test_reaction_prompt_manifest_endpoint(client: TestClient) -> None:
    """Verify GET /ui/manifest frontdoor exposes reaction prompt and ready action card."""
    resp = client.get("/ui/manifest")
    assert resp.status_code == 200
    data = resp.json()
    assert data["service"] == "game_session"
    assert data["package"] == "@runefoble/game-session-ui"
    assert data["version"] == "0.1.0"
    assert "runefoble-combat-reaction-prompt" in data["components"]
    assert "runefoble-ready-action-card" in data["components"]

    # Test routed alias /game_session/ui/manifest
    alias_resp = client.get("/game_session/ui/manifest")
    assert alias_resp.status_code == 200
    alias_data = alias_resp.json()
    assert "runefoble-combat-reaction-prompt" in alias_data["components"]
    assert "runefoble-ready-action-card" in alias_data["components"]


def test_manifest_file_matches_advertised_manifest(client: TestClient) -> None:
    """Verify services/game_session/ui/manifest.json matches runtime advertising."""
    manifest_path = REPO_ROOT / "services/game_session/ui/manifest.json"
    assert manifest_path.is_file(), f"{manifest_path} must exist"
    manifest_data = json.loads(manifest_path.read_text(encoding="utf-8"))
    endpoint_data = client.get("/ui/manifest").json()
    assert manifest_data["service"] == endpoint_data["service"]
    assert manifest_data["package"] == endpoint_data["package"]
    assert "runefoble-combat-reaction-prompt" in manifest_data["components"]
    assert "runefoble-ready-action-card" in manifest_data["components"]
