"""Blackbox TDD tests for Wardrobe Gallery REST API, SpiceDB permissions, and Microfrontend.

Governed by:
- ADR-0013: Microfrontend Architecture and Service Component Vendoring
- Hard Invariant 1: Object-level Zanzibar authorization via SpiceDB
- Hard Invariant 6: File length limit (< 500 lines; suite module < 200 lines)
- Hard Invariant 7: Blackbox TDD with Frontdoor Setup
"""

from __future__ import annotations

from uuid import uuid4

import pytest
from character_sheet.dependencies import (
    get_spicedb_client as get_char_spicedb,
)
from fastapi.testclient import TestClient
from runefoble_auth.spicedb import SpiceDBClient

from tests.helpers.ws_identity import bearer


@pytest.mark.asyncio
async def test_blackbox_spicedb_zanzibar_authorization(char_client: TestClient):
    """Verify SpiceDB Zanzibar permissions on character wardrobe and portrait mutation."""
    spicedb: SpiceDBClient = get_char_spicedb()

    create_res = char_client.post(
        "/api/v1/characters",
        json={"name": "Evelyn the Sorcerer", "character_class": "Sorcerer", "max_hp": 25},
    )
    char_id = create_res.json()["character_id"]

    owner_id = f"user-{uuid4().hex[:6]}"
    stranger_id = f"stranger-{uuid4().hex[:6]}"

    # Grant edit permission strictly to owner_id
    await spicedb.write_relationship(
        resource_type="character",
        resource_id=str(char_id),
        relation="owner",
        subject_type="user",
        subject_id=owner_id,
    )

    # Stranger attempt must fail with 403 Forbidden
    res_stranger = char_client.post(
        f"/api/v1/characters/{char_id}/portrait/active",
        json={"image_url": "/malicious/avatar.png"},
        headers=bearer(stranger_id),
    )
    assert res_stranger.status_code == 403
    assert res_stranger.json()["detail"]["error"] == "permission_denied"

    # Owner attempt must succeed with 200 OK
    res_owner = char_client.post(
        f"/api/v1/characters/{char_id}/portrait/active",
        json={"image_url": "/sanctioned/avatar.png"},
        headers=bearer(owner_id),
    )
    assert res_owner.status_code == 200
    assert "/sanctioned/avatar.png" in res_owner.json()["base_portrait_url"]


def test_blackbox_ui_microfrontend_manifest(char_client: TestClient):
    """Verify <runefoble-wardrobe-gallery> microfrontend manifest."""
    # 1. Microfrontend manifest endpoint
    manifest_res = char_client.get("/ui/manifest")
    assert manifest_res.status_code == 200
    manifest = manifest_res.json()
    assert "runefoble-wardrobe-gallery" in manifest["components"]
    assert "runefoble-wardrobe-gallery" in manifest["tags"]
    assert any("runefoble-wardrobe-gallery.styles" in s for s in manifest.get("styles", []))
