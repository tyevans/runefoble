"""Blackbox TDD frontdoor test suite for Rules Compendium UI Microfrontend.

Governed by:
- ADR-0001: SpiceDB Zanzibar Object Authorization
- ADR-0003: UV Monorepo Workspace for Python BCs
- ADR-0004: Lit Web Components and Storybook UI
- ADR-0007: Unified API Gateway & Microservice Endpoints
- ADR-0013: Microfrontend Architecture and Service Component Vendoring
- Hard Invariant 1: SpiceDB Zanzibar object authorization
- Hard Invariant 6: File length limit (< 500 lines)
- Hard Invariant 7: Blackbox TDD with Frontdoor Setup
"""

from __future__ import annotations

import json
from pathlib import Path
from uuid import uuid4

import pytest
from fastapi.testclient import TestClient
from rules_compendium.dependencies import get_spicedb_client
from rules_compendium.main import app

REPO_ROOT = Path(__file__).resolve().parent.parent


@pytest.fixture
def client() -> TestClient:
    with TestClient(app) as test_client:
        yield test_client


# ---------------------------------------------------------------------------
# 1. Microfrontend Manifest & Package Structure Integrity
# ---------------------------------------------------------------------------


def test_compendium_manifest_endpoint(client: TestClient) -> None:
    """Verify GET /ui/manifest frontdoor exposes correct microfrontend metadata."""
    resp = client.get("/ui/manifest")
    assert resp.status_code == 200
    data = resp.json()
    assert data["service"] == "rules_compendium"
    assert data["package"] == "@runefoble/rules-compendium-ui"
    assert data["version"] == "0.1.0"
    assert "runefoble-rules-compendium" in data["components"]
    assert "runefoble-rules-lookup" in data["components"]
    assert "runefoble-encounter-builder" in data["components"]
    assert "runefoble-homebrew-creator" in data["components"]


def test_manifest_file_matches_advertised_manifest() -> None:
    """Verify services/rules_compendium/ui/manifest.json matches runtime advertising."""
    manifest_path = REPO_ROOT / "services/rules_compendium/ui/manifest.json"
    assert manifest_path.is_file(), f"{manifest_path} must exist"

    manifest_data = json.loads(manifest_path.read_text(encoding="utf-8"))
    assert manifest_data["service"] == "rules_compendium"
    assert manifest_data["package"] == "@runefoble/rules-compendium-ui"
    assert manifest_data["version"] == "0.1.0"
    assert "runefoble-rules-compendium" in manifest_data["components"]
    assert "runefoble-rules-lookup" in manifest_data["components"]
    assert "runefoble-encounter-builder" in manifest_data["components"]
    assert "runefoble-homebrew-creator" in manifest_data["components"]


def test_typescript_elements_source_and_custom_elements() -> None:
    """Verify UI package configuration, exports, and Custom Element decorators."""
    ui_dir = REPO_ROOT / "services/rules_compendium/ui"

    pkg_json = json.loads((ui_dir / "package.json").read_text(encoding="utf-8"))
    assert pkg_json["name"] == "@runefoble/rules-compendium-ui"
    assert pkg_json["exports"]["."].endswith("index.ts")
    assert "./runefoble-rules-compendium" in pkg_json["exports"]
    assert "./runefoble-rules-lookup" in pkg_json["exports"]
    assert "./runefoble-encounter-builder" in pkg_json["exports"]
    assert "./runefoble-homebrew-creator" in pkg_json["exports"]

    assert (ui_dir / "tsconfig.json").is_file()
    assert (ui_dir / "src/index.ts").is_file()
    assert (ui_dir / "src/types.ts").is_file()
    assert (ui_dir / "src/runefoble-rules-compendium.styles.ts").is_file()

    # Check runefoble-rules-compendium root component (< 180 lines)
    comp_file = ui_dir / "src/runefoble-rules-compendium.ts"
    assert comp_file.is_file()
    comp_src = comp_file.read_text(encoding="utf-8")
    assert "@customElement('runefoble-rules-compendium')" in comp_src
    assert "class RunefobleRulesCompendium" in comp_src
    assert len(comp_src.splitlines()) < 180, "runefoble-rules-compendium.ts must be < 180 lines"

    # Check runefoble-homebrew-creator component (< 200 lines)
    hb_file = ui_dir / "src/runefoble-homebrew-creator.ts"
    assert hb_file.is_file()
    hb_src = hb_file.read_text(encoding="utf-8")
    assert "@customElement('runefoble-homebrew-creator')" in hb_src
    assert "class RunefobleHomebrewCreator" in hb_src
    assert len(hb_src.splitlines()) < 200, (
        "runefoble-homebrew-creator.ts must be strictly < 200 lines"
    )

    # Check runefoble-rules-lookup component
    lookup_file = ui_dir / "src/runefoble-rules-lookup.ts"
    assert lookup_file.is_file()
    lookup_src = lookup_file.read_text(encoding="utf-8")
    assert "@customElement('runefoble-rules-lookup')" in lookup_src
    assert "class RunefobleRulesLookup" in lookup_src

    # Check runefoble-encounter-builder component
    enc_file = ui_dir / "src/runefoble-encounter-builder.ts"
    assert enc_file.is_file()
    enc_src = enc_file.read_text(encoding="utf-8")
    assert "@customElement('runefoble-encounter-builder')" in enc_src
    assert "class RunefobleEncounterBuilder" in enc_src


def test_modular_compendium_styles_architecture() -> None:
    """Verify modular styles decomposition under services/rules_compendium/ui/src/styles/ per TASK-0185.

    Governed by:
    - ADR-0012: Design System Theming and Bauhaus Modernism
    - ADR-0013: Microfrontend Architecture and Service Component Vendoring
    - Hard Invariant 6: File length limit (< 500 lines, sub-stylesheets strictly < 150 lines)
    """
    ui_dir = REPO_ROOT / "services/rules_compendium/ui"
    styles_dir = ui_dir / "src/styles"
    assert styles_dir.is_dir(), f"{styles_dir} directory must exist"

    # 1. Base & Layout Styles (< 100 lines, strictly < 150 lines)
    base_file = styles_dir / "compendium-base.styles.ts"
    assert base_file.is_file()
    base_lines = len(base_file.read_text(encoding="utf-8").splitlines())
    assert base_lines < 100, f"compendium-base.styles.ts must be < 100 lines, got {base_lines}"
    assert "export const compendiumBaseStyles" in base_file.read_text(encoding="utf-8")

    # 2. Encounter Builder Styles (< 120 lines, strictly < 150 lines)
    enc_styles_file = styles_dir / "encounter-builder.styles.ts"
    assert enc_styles_file.is_file()
    enc_lines = len(enc_styles_file.read_text(encoding="utf-8").splitlines())
    assert enc_lines < 120, f"encounter-builder.styles.ts must be < 120 lines, got {enc_lines}"
    assert "export const encounterBuilderStyles" in enc_styles_file.read_text(encoding="utf-8")

    # 3. Homebrew Form Styles (< 110 lines, strictly < 150 lines)
    hb_styles_file = styles_dir / "homebrew-form.styles.ts"
    assert hb_styles_file.is_file()
    hb_lines = len(hb_styles_file.read_text(encoding="utf-8").splitlines())
    assert hb_lines < 110, f"homebrew-form.styles.ts must be < 110 lines, got {hb_lines}"
    assert "export const homebrewFormStyles" in hb_styles_file.read_text(encoding="utf-8")

    # 4. Styles barrel index.ts
    styles_index = styles_dir / "index.ts"
    assert styles_index.is_file()
    styles_index_content = styles_index.read_text(encoding="utf-8")
    assert "compendium-base.styles.ts" in styles_index_content
    assert "encounter-builder.styles.ts" in styles_index_content
    assert "homebrew-form.styles.ts" in styles_index_content

    # 5. Aggregator Facade (< 80 lines, < 60 lines)
    facade_file = ui_dir / "src/runefoble-rules-compendium.styles.ts"
    assert facade_file.is_file()
    facade_lines = len(facade_file.read_text(encoding="utf-8").splitlines())
    assert facade_lines < 80, (
        f"runefoble-rules-compendium.styles.ts must be strictly < 80 lines, got {facade_lines}"
    )
    assert facade_lines < 60, (
        f"runefoble-rules-compendium.styles.ts must be < 60 lines, got {facade_lines}"
    )
    facade_content = facade_file.read_text(encoding="utf-8")
    assert "export const compendiumStyles" in facade_content
    assert "compendiumBaseStyles" in facade_content
    assert "encounterBuilderStyles" in facade_content
    assert "homebrewFormStyles" in facade_content


def test_storybook_stories_definition() -> None:
    """Verify Storybook stories include Search, Monster stat cards, CR Encounter balance, and Homebrew."""
    stories_file = (
        REPO_ROOT / "services/rules_compendium/ui/src/runefoble-rules-compendium.stories.ts"
    )
    assert stories_file.is_file()
    content = stories_file.read_text(encoding="utf-8")
    assert "Default" in content
    assert "SearchResultsWithLatency" in content
    assert "MonsterStatCards" in content
    assert "CREncounterBalanceCalculator" in content
    assert "HomebrewCreator" in content
    assert "DedicatedHomebrewCreator" in content
    assert "runefoble-rules-compendium" in content
    assert "runefoble-homebrew-creator" in content


def test_frontend_app_shell_forwarding_export() -> None:
    """Verify frontend/src/components/ re-exports the microfrontend per ADR-0013."""
    forwarding_file = REPO_ROOT / "frontend/src/components/runefoble-rules-compendium.ts"
    assert forwarding_file.is_file()
    content = forwarding_file.read_text(encoding="utf-8")
    assert "@runefoble/rules-compendium-ui" in content

    index_file = REPO_ROOT / "frontend/src/index.ts"
    assert index_file.is_file()
    index_content = index_file.read_text(encoding="utf-8")
    assert "runefoble-rules-compendium" in index_content


# ---------------------------------------------------------------------------
# 2. REST Frontdoor Data Binding Integration
# ---------------------------------------------------------------------------


def test_rest_data_binding_rules_search(client: TestClient) -> None:
    """Verify REST search frontdoor delivers schemas matching microfrontend data bindings."""
    resp = client.get("/api/v1/compendium/rules/search?query=fire+damage")
    assert resp.status_code == 200
    data = resp.json()

    # Matches RuleSearchResponse contract
    assert "query" in data
    assert "results_count" in data
    assert "took_ms" in data
    assert "results" in data
    assert isinstance(data["results"], list)
    assert data["results_count"] >= 1
    assert data["took_ms"] < 50.0  # Sub-50ms SLA

    # Check RuleSearchResultItem data binding properties
    item = data["results"][0]
    assert "category" in item
    assert "name" in item
    assert "score" in item
    assert "summary" in item
    assert "details" in item
    assert "is_homebrew" in item


def test_rest_data_binding_monster_stat_block(client: TestClient) -> None:
    """Verify monster lookup delivers complete stat block for UI rendering."""
    resp = client.get("/api/v1/compendium/monsters/Goblin")
    assert resp.status_code == 200
    monster = resp.json()

    assert monster["name"] == "Goblin"
    assert monster["challenge_rating"] == 0.25
    assert monster["armor_class"] == 15
    assert monster["hit_points"] == 7
    assert monster["role"] == "skirmisher"
    assert "stats" in monster
    assert monster["stats"]["DEX"] == 14


def test_rest_data_binding_spell_and_condition(client: TestClient) -> None:
    """Verify spell and condition lookups match microfrontend card schemas."""
    # Spell
    s_resp = client.get("/api/v1/compendium/spells/Hold%20Person")
    assert s_resp.status_code == 200
    spell = s_resp.json()
    assert spell["name"] == "Hold Person"
    assert spell["level"] == 2
    assert spell["school"] == "Enchantment"
    assert "description" in spell

    # Condition
    c_resp = client.get("/api/v1/compendium/conditions/Paralyzed")
    assert c_resp.status_code == 200
    cond = c_resp.json()
    assert cond["name"] == "Paralyzed"
    assert isinstance(cond["effects"], list)
    assert len(cond["effects"]) >= 2


def test_rest_data_binding_encounter_balance(client: TestClient) -> None:
    """Verify encounter balancing delivers thresholds and monster recommendations matching UI builder."""
    payload = {
        "party_levels": [3, 3, 3, 3],
        "target_difficulty": "Medium",
    }
    resp = client.post("/api/v1/compendium/encounters/balance", json=payload)
    assert resp.status_code == 200
    data = resp.json()

    # Matches EncounterBalanceResponse contract
    assert "encounter_id" in data
    assert data["party_size"] == 4
    assert data["target_difficulty"] == "Medium"
    assert "total_party_xp_threshold" in data
    thresholds = data["total_party_xp_threshold"]
    assert thresholds["easy"] == 300
    assert thresholds["medium"] == 600
    assert thresholds["hard"] == 900
    assert thresholds["deadly"] == 1600

    assert "monsters" in data
    assert len(data["monsters"]) >= 1
    rec = data["monsters"][0]
    assert "name" in rec
    assert "cr" in rec
    assert "xp" in rec
    assert "count" in rec
    assert "role" in rec
    assert "subtotal_xp" in rec

    assert data["adjusted_xp"] > 0
    assert data["multiplier"] >= 1.0
    assert "tactical_summary" in data


# ---------------------------------------------------------------------------
# 3. SpiceDB Zanzibar Fine-Grained Authorization
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_spicedb_zanzibar_authorization_on_homebrew(client: TestClient) -> None:
    """Verify homebrew creation and scoped search enforce SpiceDB Zanzibar authorization."""
    campaign_id = str(uuid4())
    dm_user = f"dm-{uuid4().hex[:6]}"
    player_user = f"player-{uuid4().hex[:6]}"
    stranger = f"stranger-{uuid4().hex[:6]}"

    spicedb = get_spicedb_client()

    # Assign DM role
    await spicedb.write_relationship(
        resource_type="campaign",
        resource_id=campaign_id,
        relation="dungeon_master",
        subject_type="user",
        subject_id=dm_user,
    )
    # Assign Player role
    await spicedb.write_relationship(
        resource_type="campaign",
        resource_id=campaign_id,
        relation="player",
        subject_type="user",
        subject_id=player_user,
    )

    homebrew_payload = {
        "campaign_id": campaign_id,
        "rule_type": "monster",
        "title": "Abyssal Shadowstalker",
        "content": {
            "challenge_rating": 3.0,
            "creature_type": "fiend",
            "armor_class": 16,
            "hit_points": 45,
            "xp": 700,
            "role": "skirmisher",
            "description": "A stealthy fiend summoned from the Shadowfell.",
        },
    }

    # 1. Unauthorized user receives 403 Forbidden
    resp_unauth = client.post(
        "/api/v1/compendium/homebrew",
        json=homebrew_payload,
        headers={"x-user-id": stranger},
    )
    assert resp_unauth.status_code == 403
    assert "Forbidden" in resp_unauth.json()["detail"]

    # 2. DM registers homebrew successfully
    resp_dm = client.post(
        "/api/v1/compendium/homebrew",
        json=homebrew_payload,
        headers={"x-user-id": dm_user},
    )
    assert resp_dm.status_code == 200
    hb_data = resp_dm.json()
    assert hb_data["title"] == "Abyssal Shadowstalker"
    assert hb_data["author_id"] == dm_user
    assert hb_data["status"] == "registered"

    # 3. Campaign player can search and see the homebrew rule
    resp_search_player = client.get(
        f"/api/v1/compendium/rules/search?query=Shadowstalker&campaign_id={campaign_id}",
        headers={"x-user-id": player_user},
    )
    assert resp_search_player.status_code == 200
    results_player = resp_search_player.json()["results"]
    assert any(
        r["name"] == "Abyssal Shadowstalker" and r["is_homebrew"] is True for r in results_player
    )

    # 4. Stranger cannot see the campaign homebrew rule
    resp_search_stranger = client.get(
        f"/api/v1/compendium/rules/search?query=Shadowstalker&campaign_id={campaign_id}",
        headers={"x-user-id": stranger},
    )
    assert resp_search_stranger.status_code == 200
    results_stranger = resp_search_stranger.json()["results"]
    assert not any(r["name"] == "Abyssal Shadowstalker" for r in results_stranger)
