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

from .conftest import REPO_ROOT


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
        headers={"X-User-Id": stranger_id},
    )
    assert res_stranger.status_code == 403
    assert (
        "Forbidden" in res_stranger.json()["detail"]
        or "permission" in res_stranger.json()["detail"]
    )

    # Owner attempt must succeed with 200 OK
    res_owner = char_client.post(
        f"/api/v1/characters/{char_id}/portrait/active",
        json={"image_url": "/sanctioned/avatar.png"},
        headers={"X-User-Id": owner_id},
    )
    assert res_owner.status_code == 200
    assert "/sanctioned/avatar.png" in res_owner.json()["base_portrait_url"]


def test_blackbox_ui_microfrontend_manifest_and_storybook(char_client: TestClient):
    """Verify <runefoble-wardrobe-gallery> microfrontend element and Storybook stories."""
    # 1. Microfrontend manifest endpoint
    manifest_res = char_client.get("/ui/manifest")
    assert manifest_res.status_code == 200
    manifest = manifest_res.json()
    assert "runefoble-wardrobe-gallery" in manifest["components"]
    assert "runefoble-wardrobe-gallery" in manifest["tags"]
    assert any("runefoble-wardrobe-gallery.styles" in s for s in manifest.get("styles", []))

    # 2. Lit Component TypeScript source & Companion Styles
    comp_file = REPO_ROOT / "services/character_sheet/ui/src/runefoble-wardrobe-gallery.ts"
    assert comp_file.is_file()
    comp_src = comp_file.read_text(encoding="utf-8")
    assert "@customElement('runefoble-wardrobe-gallery')" in comp_src
    assert "wardrobeGalleryStyles" in comp_src
    assert "portrait-selected" in comp_src
    assert "generate-wardrobe" in comp_src

    styles_file = REPO_ROOT / "services/character_sheet/ui/src/runefoble-wardrobe-gallery.styles.ts"
    assert styles_file.is_file()
    styles_src = styles_file.read_text(encoding="utf-8")
    assert "wardrobeGalleryStyles" in styles_src
    assert "--rf-bg-card" in styles_src

    # 3. Storybook stories
    stories_file = (
        REPO_ROOT / "services/character_sheet/ui/src/runefoble-wardrobe-gallery.stories.ts"
    )
    assert stories_file.is_file()
    stories_src = stories_file.read_text(encoding="utf-8")
    assert "HealthyBase" in stories_src
    assert "BloodiedInjury" in stories_src
    assert "PoisonedAffliction" in stories_src
    assert "GalaAttireMasquerade" in stories_src


def test_blackbox_wardrobe_gallery_styles_and_subcomponents_modular_decomposition():
    """Verify TASK-0131: Wardrobe gallery styles extracted to companion *.styles.ts module and line limits (<250 lines)."""
    comp_file = REPO_ROOT / "services/character_sheet/ui/src/runefoble-wardrobe-gallery.ts"
    styles_file = REPO_ROOT / "services/character_sheet/ui/src/runefoble-wardrobe-gallery.styles.ts"

    assert comp_file.is_file(), f"{comp_file} must exist"
    assert styles_file.is_file(), f"{styles_file} must exist"

    comp_lines = len(comp_file.read_text(encoding="utf-8").splitlines())
    styles_lines = len(styles_file.read_text(encoding="utf-8").splitlines())

    assert comp_lines < 250, f"Component file has {comp_lines} lines (expected < 250)"
    assert styles_lines < 250, f"Styles file has {styles_lines} lines (expected < 250)"

    comp_src = comp_file.read_text(encoding="utf-8")
    assert "renderConditionBadge" in comp_src
    assert "renderConditionBadges" in comp_src
    assert "renderVariantCard" in comp_src
    assert "renderActiveSection" in comp_src
    assert "renderForgePanel" in comp_src
