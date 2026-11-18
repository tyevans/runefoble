"""Microfrontend manifest and component delivery tests for Soundscape UI (TASK-0154).

Governed by:
- ADR-0004: Lit Web Components and Storybook UI
- ADR-0013: Microfrontend Architecture and Service Component Vendoring
- Hard Invariant 6: File length limit (< 500 lines)
- Hard Invariant 7: Blackbox TDD with Frontdoor Setup
"""

from __future__ import annotations

import json

from fastapi.testclient import TestClient

from .conftest import REPO_ROOT


def test_soundscape_manifest_endpoint(client: TestClient) -> None:
    """Verify GET /ui/manifest frontdoor exposes correct microfrontend metadata."""
    resp = client.get("/ui/manifest")
    assert resp.status_code == 200
    data = resp.json()
    assert data["service"] == "soundscape"
    assert data["package"] == "@runefoble/soundscape-ui"
    assert data["version"] == "0.1.0"
    assert "runefoble-soundscape-controls" in data["components"]
    assert "runefoble-soundscape-controls" in data["tags"]
    assert any("runefoble-soundscape-controls.styles" in s for s in data["styles"])
    assert any("index.ts" in s for s in data["scripts"])


def test_manifest_file_matches_advertised_manifest(client: TestClient) -> None:
    """Verify services/soundscape/ui/manifest.json matches runtime advertising."""
    manifest_path = REPO_ROOT / "services/soundscape/ui/manifest.json"
    manifest_data = json.loads(manifest_path.read_text(encoding="utf-8"))
    endpoint_data = client.get("/ui/manifest").json()
    for field in ("service", "package", "components", "tags"):
        assert manifest_data[field] == endpoint_data[field]
