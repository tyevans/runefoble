"""Microfrontend manifest and component delivery tests for West Marches UI (TASK-0176).

Governed by:
- ADR-0003: UV Monorepo Workspace for Python BCs
- ADR-0013: Microfrontend Architecture and Service Component Vendoring
- Hard Invariant 6: File length limit (< 500 lines, target < 100 lines)
- Hard Invariant 7: Blackbox TDD with Frontdoor Setup
"""

from __future__ import annotations

from fastapi.testclient import TestClient


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
