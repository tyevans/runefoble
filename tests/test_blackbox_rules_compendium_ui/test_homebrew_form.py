"""Blackbox TDD tests for Homebrew Creator form and Zanzibar authorization.

Governed by ADR-0001, ADR-0003, ADR-0004, ADR-0013, and Hard Invariants 1 & 7.
"""

from __future__ import annotations

from typing import Any
from uuid import uuid4

import pytest
from fastapi.testclient import TestClient
from rules_compendium.dependencies import get_spicedb_client

from .conftest import REPO_ROOT


@pytest.mark.asyncio
async def test_spicedb_zanzibar_authorization_on_homebrew(
    client: TestClient, sample_homebrew_payload: dict[str, Any]
) -> None:
    """Verify homebrew creation and scoped search enforce SpiceDB Zanzibar authorization."""
    campaign_id = str(uuid4())
    dm_user, player_user, stranger = (
        f"dm-{uuid4().hex[:6]}",
        f"pl-{uuid4().hex[:6]}",
        f"st-{uuid4().hex[:6]}",
    )

    spicedb = get_spicedb_client()
    await spicedb.write_relationship("campaign", campaign_id, "dungeon_master", "user", dm_user)
    await spicedb.write_relationship("campaign", campaign_id, "player", "user", player_user)

    payload = dict(sample_homebrew_payload, campaign_id=campaign_id)

    # 1. Unauthorized user receives 403 Forbidden
    resp_unauth = client.post(
        "/api/v1/compendium/homebrew", json=payload, headers={"x-user-id": stranger}
    )
    assert resp_unauth.status_code == 403
    assert "Forbidden" in resp_unauth.json()["detail"]

    # 2. DM registers homebrew successfully
    resp_dm = client.post(
        "/api/v1/compendium/homebrew", json=payload, headers={"x-user-id": dm_user}
    )
    assert resp_dm.status_code == 200
    assert resp_dm.json()["title"] == "Abyssal Shadowstalker"
    assert resp_dm.json()["author_id"] == dm_user

    # 3. Campaign player can search and see the homebrew rule
    resp_player = client.get(
        f"/api/v1/compendium/rules/search?query=Shadowstalker&campaign_id={campaign_id}",
        headers={"x-user-id": player_user},
    )
    assert resp_player.status_code == 200
    assert any(
        r["name"] == "Abyssal Shadowstalker" and r["is_homebrew"] is True
        for r in resp_player.json()["results"]
    )

    # 4. Stranger cannot see the campaign homebrew rule
    resp_stranger = client.get(
        f"/api/v1/compendium/rules/search?query=Shadowstalker&campaign_id={campaign_id}",
        headers={"x-user-id": stranger},
    )
    assert resp_stranger.status_code == 200
    assert not any(r["name"] == "Abyssal Shadowstalker" for r in resp_stranger.json()["results"])


def test_homebrew_creator_component_and_styles() -> None:
    """Verify homebrew creator custom element and modular styles per TASK-0179."""
    ui_dir = REPO_ROOT / "services/rules_compendium/ui"
    hb_file = ui_dir / "src/runefoble-homebrew-creator.ts"
    assert hb_file.is_file()
    hb_src = hb_file.read_text(encoding="utf-8")
    assert "@customElement('runefoble-homebrew-creator')" in hb_src
    assert len(hb_src.splitlines()) < 200

    styles_file = ui_dir / "src/styles/homebrew-form.styles.ts"
    assert styles_file.is_file()
    assert len(styles_file.read_text(encoding="utf-8").splitlines()) < 110
    assert "export const homebrewFormStyles" in styles_file.read_text(encoding="utf-8")

    stories = (ui_dir / "src/runefoble-rules-compendium.stories.ts").read_text(encoding="utf-8")
    assert "HomebrewCreator" in stories
    assert "DedicatedHomebrewCreator" in stories
