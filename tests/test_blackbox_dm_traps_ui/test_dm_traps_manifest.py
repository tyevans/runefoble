"""Manifest and microfrontend component delivery tests for DM Traps UI (TASK-0159).

Governed by:
- ADR-0004: Lit Web Components and Storybook UI
- ADR-0012: Theming System and Accessibility Contrast Invariants
- ADR-0013: Microfrontend Architecture and Service Component Vendoring
- Hard Invariant 6: File length limit (< 500 lines)
- Hard Invariant 7: Blackbox TDD with Frontdoor Setup
"""

from __future__ import annotations

import asyncio
import json
from uuid import uuid4

import pytest
from fastapi.testclient import TestClient
from runefoble_auth.spicedb import MockSpiceDBClient

from tests.helpers.ws_identity import SIGNING_ISSUER

from .conftest import REPO_ROOT


def bearer(sub: str) -> dict[str, str]:
    """Return the Authorization header for a token that the shared test issuer signs for `sub`."""
    return {"Authorization": f"Bearer {SIGNING_ISSUER.mint(sub)}"}


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


@pytest.mark.asyncio
async def test_frontdoor_contract_integration(
    client: TestClient, spicedb: MockSpiceDBClient
) -> None:
    """Verify UI action payloads conform with backend board API frontdoors."""
    board_id = f"board-{uuid4().hex[:8]}"
    campaign_id = f"camp-{uuid4().hex[:8]}"
    dm_user = f"dm-{uuid4().hex[:6]}"

    await spicedb.write_relationship("campaign", campaign_id, "dungeon_master", "user", dm_user)

    # 1. Initialize board
    init_res = client.post(
        "/api/v1/boards",
        json={"campaign_id": campaign_id, "board_id": board_id, "cols": 15, "rows": 15},
        headers=bearer(dm_user),
    )
    assert init_res.status_code == 200

    # 2. Place trap using parameters defined in UI trap preset
    trap_res = client.post(
        f"/api/v1/boards/{board_id}/traps",
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
        headers=bearer(dm_user),
    )
    assert trap_res.status_code == 201
    trap_data = trap_res.json()
    assert trap_data["name"] == "Spike Pit"
    assert trap_data["trigger_type"] == "step"

    # 3. Execute map switch using parameters defined in UI map switcher
    switch_res = client.post(
        f"/api/v1/boards/{board_id}/switch-map",
        json={
            "new_map_id": "dungeon_lvl2",
            "cols": 20,
            "rows": 20,
            "background_image_url": "https://assets.runefoble.com/maps/dungeon_lvl2.png",
            "token_teleports": {"valeros": [10, 15]},
        },
        headers=bearer(dm_user),
    )
    assert switch_res.status_code == 200
    switch_data = switch_res.json()
    assert switch_data["new_map_id"] == "dungeon_lvl2"
    assert switch_data["cols"] == 20
    assert switch_data["rows"] == 20


BOARD_CAMPAIGN = "camp-board-fixture"


@pytest.fixture(autouse=True)
def _board_campaign_dm(spicedb):
    """Make `user-test` the DM of the campaign that every board in this module belongs to."""
    asyncio.run(
        spicedb.write_relationship(
            resource_type="campaign",
            resource_id=BOARD_CAMPAIGN,
            relation="dungeon_master",
            subject_type="user",
            subject_id="user-test",
        )
    )
