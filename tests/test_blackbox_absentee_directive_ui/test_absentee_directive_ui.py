"""Blackbox TDD frontdoor test suite for Absentee Mobile Directive and Remote Voting Microfrontend.

Governed by:
- ADR-0004: Lit + Vite Microfrontends with Storybook
- ADR-0012: CSS Custom Properties & Semantic Dark/Light Invariants
- ADR-0013: Modular Microfrontend Decomposition
- Hard Invariant 6: File length limit (< 500 lines)
- Hard Invariant 7: Blackbox TDD with Frontdoor Setup
"""

from __future__ import annotations

import pytest
from fastapi.testclient import TestClient
from the_watcher.main import app


@pytest.fixture
def client() -> TestClient:
    return TestClient(app)


def test_the_watcher_ui_manifest_advertises_absentee_components(client: TestClient) -> None:
    """Verify GET /ui/manifest frontdoor exposes absentee directive and vote card."""
    for path in ["/ui/manifest", "/the-watcher/ui/manifest"]:
        resp = client.get(path)
        assert resp.status_code == 200, f"Failed at {path}"
        data = resp.json()
        assert data["service"] == "the_watcher"
        assert data["package"] == "@runefoble/the-watcher-ui"
        assert data["version"] == "0.1.0"
        assert "runefoble-absentee-directive" in data["components"]
        assert "runefoble-absentee-vote-card" in data["components"]
        assert "runefoble-absentee-directive" in data["tags"]
        assert "runefoble-absentee-vote-card" in data["tags"]
