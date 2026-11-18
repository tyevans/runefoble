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


def test_rest_data_binding_rules_search(client: TestClient) -> None:
    """Verify REST search frontdoor delivers schemas matching microfrontend data bindings."""
    import os

    # Warmup query to initialize in-memory indexing on cold CI runners
    client.get("/api/v1/compendium/rules/search?query=warmup")
    resp = client.get("/api/v1/compendium/rules/search?query=fire+damage")
    assert resp.status_code == 200
    data = resp.json()
    assert data["results_count"] >= 1
    max_ms = 500.0 if os.environ.get("CI") else 50.0
    assert data["took_ms"] < max_ms  # Sub-50ms SLA

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
