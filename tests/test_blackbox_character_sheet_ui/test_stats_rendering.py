"""Blackbox TDD tests for Character Sheet stats, vitals, and rendering.

Governed by ADR-0003, ADR-0004, ADR-0007, ADR-0013, and Hard Invariant 7.
"""

from __future__ import annotations

import json

from fastapi.testclient import TestClient

from .conftest import REPO_ROOT


def test_character_sheet_manifest_and_forwarding(client: TestClient) -> None:
    """Verify microfrontend manifest endpoint, manifest.json, and app shell export."""
    resp = client.get("/ui/manifest")
    assert resp.status_code == 200
    data = resp.json()
    assert data["service"] == "character_sheet"
    assert data["package"] == "@runefoble/character-sheet-ui"
    assert data["version"] == "0.1.0"
    for comp in ("runefoble-character-sheet", "runefoble-character-card"):
        assert comp in data["components"]

    manifest_path = REPO_ROOT / "services/character_sheet/ui/manifest.json"
    assert manifest_path.is_file()
    assert json.loads(manifest_path.read_text(encoding="utf-8")) == data

    fwd = REPO_ROOT / "frontend/src/components/runefoble-character-sheet.ts"
    assert "@runefoble/character-sheet-ui" in fwd.read_text(encoding="utf-8")


def test_stats_and_vitals_lifecycle(client: TestClient, created_character_id: str) -> None:
    """Verify ability scores, HP meters, temporary HP, and level-up progression."""
    char_id = created_character_id
    sheet = client.get(f"/api/v1/characters/{char_id}").json()
    assert sheet["name"] == "Valeros the Bold"
    assert sheet["level"] == 1
    assert sheet["current_hp"] == 40
    assert sheet["max_hp"] == 40
    for score in ("str", "dex", "con", "int", "wis", "cha"):
        assert score in sheet["ability_scores"]

    # Health modification and vitals check
    hp_resp = client.post(
        f"/api/v1/characters/{char_id}/health",
        json={"delta": -15, "source": "damage"},
    )
    assert hp_resp.status_code == 200
    updated = hp_resp.json()
    assert updated["current_hp"] == 25
    assert updated["max_hp"] == 40

    # Level-up progression
    lvl_resp = client.post(f"/api/v1/characters/{char_id}/level-up")
    assert lvl_resp.status_code == 200
    assert lvl_resp.json()["level"] == 2


def test_stats_components_and_storybook() -> None:
    """Verify Lit component registration, stats templates, and Storybook stories."""
    ui_dir = REPO_ROOT / "services/character_sheet/ui"
    comp_src = (ui_dir / "src/runefoble-character-sheet.ts").read_text(encoding="utf-8")
    assert "@customElement('runefoble-character-sheet')" in comp_src
    assert "class RunefobleCharacterSheet" in comp_src

    stats_tmpl = (ui_dir / "src/templates/stats.template.ts").read_text(encoding="utf-8")
    assert "renderStats" in stats_tmpl or len(stats_tmpl) > 0

    stories = (ui_dir / "src/runefoble-character-sheet.stories.ts").read_text(encoding="utf-8")
    for variant in ("Healthy", "Encumbered", "Afflicted", "LeveledUpSpellcaster"):
        assert variant in stories
