"""Blackbox TDD frontdoor test suite for Faction Espionage and Alert Feeds Microfrontend.

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

from tests.helpers.ws_identity import SIGNING_ISSUER

pytestmark = pytest.mark.usefixtures("trusted_ws_issuer")


@pytest.fixture
def client() -> TestClient:
    return TestClient(app, headers={"Authorization": f"Bearer {SIGNING_ISSUER.mint('test-user')}"})


def test_the_watcher_ui_manifest_advertises_faction_espionage(client: TestClient) -> None:
    """Verify GET /ui/manifest frontdoor exposes runefoble-faction-espionage component."""
    for path in ["/ui/manifest"]:
        resp = client.get(path)
        assert resp.status_code == 200, f"Failed at {path}"
        data = resp.json()
        assert data["service"] == "the_watcher"
        assert data["package"] == "@runefoble/the-watcher-ui"
        assert data["version"] == "0.1.0"
        assert "runefoble-faction-espionage" in data["components"]
        assert "runefoble-faction-radar" in data["components"]
        assert "runefoble-autonomous-dm" in data["components"]
        assert "runefoble-watcher-feed" in data["components"]
