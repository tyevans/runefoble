"""Blackbox TDD tests for SRD rules hybrid search and entity lookup.

Governed by ADR-0003, ADR-0004, ADR-0013, and Hard Invariant 7.
"""

from __future__ import annotations

import json

from fastapi.testclient import TestClient

from .conftest import REPO_ROOT


def test_compendium_manifest_and_exports(client: TestClient) -> None:
    """Verify microfrontend manifest and App Shell export binding."""
    resp = client.get("/ui/manifest")
    assert resp.status_code == 200
    data = resp.json()
    assert data["service"] == "rules_compendium"
    assert data["package"] == "@runefoble/rules-compendium-ui"
    assert data["version"] == "0.1.0"
    for comp in (
        "runefoble-rules-compendium",
        "runefoble-rules-lookup",
        "runefoble-encounter-builder",
        "runefoble-homebrew-creator",
    ):
        assert comp in data["components"]

    manifest_path = REPO_ROOT / "services/rules_compendium/ui/manifest.json"
    assert manifest_path.is_file()
    assert json.loads(manifest_path.read_text(encoding="utf-8")) == data

    fwd = REPO_ROOT / "frontend/src/components/runefoble-rules-compendium.ts"
    assert "@runefoble/rules-compendium-ui" in fwd.read_text(encoding="utf-8")


def test_rest_data_binding_rules_search(client: TestClient) -> None:
    """Verify REST search frontdoor delivers schemas matching microfrontend data bindings."""
    resp = client.get("/api/v1/compendium/rules/search?query=fire+damage")
    assert resp.status_code == 200
    data = resp.json()
    assert data["results_count"] >= 1
    assert data["took_ms"] < 50.0  # Sub-50ms SLA

    item = data["results"][0]
    for key in ("category", "name", "score", "summary", "details", "is_homebrew"):
        assert key in item


def test_rest_data_binding_monster_spell_condition(client: TestClient) -> None:
    """Verify monster, spell, and condition lookups match microfrontend card schemas."""
    m_resp = client.get("/api/v1/compendium/monsters/Goblin")
    assert m_resp.status_code == 200
    monster = m_resp.json()
    assert monster["name"] == "Goblin"
    assert monster["challenge_rating"] == 0.25
    assert monster["armor_class"] == 15
    assert monster["hit_points"] == 7
    assert monster["role"] == "skirmisher"
    assert monster["stats"]["DEX"] == 14

    s_resp = client.get("/api/v1/compendium/spells/Hold%20Person")
    assert s_resp.status_code == 200
    spell = s_resp.json()
    assert spell["name"] == "Hold Person"
    assert spell["level"] == 2
    assert spell["school"] == "Enchantment"

    c_resp = client.get("/api/v1/compendium/conditions/Paralyzed")
    assert c_resp.status_code == 200
    cond = c_resp.json()
    assert cond["name"] == "Paralyzed"
    assert len(cond["effects"]) >= 2


def test_rules_lookup_components_and_styles() -> None:
    """Verify UI components, custom elements, and modular base styles."""
    ui_dir = REPO_ROOT / "services/rules_compendium/ui"
    comp_src = (ui_dir / "src/runefoble-rules-compendium.ts").read_text(encoding="utf-8")
    assert "@customElement('runefoble-rules-compendium')" in comp_src
    assert len(comp_src.splitlines()) < 180

    lookup_src = (ui_dir / "src/runefoble-rules-lookup.ts").read_text(encoding="utf-8")
    assert "@customElement('runefoble-rules-lookup')" in lookup_src

    base_styles = (ui_dir / "src/styles/compendium-base.styles.ts").read_text(encoding="utf-8")
    assert "export const compendiumBaseStyles" in base_styles
    assert len(base_styles.splitlines()) < 100

    facade = (ui_dir / "src/runefoble-rules-compendium.styles.ts").read_text(encoding="utf-8")
    assert "export const compendiumStyles" in facade
    assert len(facade.splitlines()) < 60
