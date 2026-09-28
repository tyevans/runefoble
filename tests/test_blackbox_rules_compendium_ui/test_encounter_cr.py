"""Blackbox TDD tests for Encounter Builder CR balancing and components.

Governed by ADR-0003, ADR-0004, ADR-0013, and Hard Invariant 7.
"""

from __future__ import annotations

import json

from fastapi.testclient import TestClient

from .conftest import REPO_ROOT


def test_rest_data_binding_encounter_balance(client: TestClient) -> None:
    """Verify encounter balancing delivers thresholds and monster recommendations."""
    payload = {
        "party_levels": [3, 3, 3, 3],
        "target_difficulty": "Medium",
    }
    resp = client.post("/api/v1/compendium/encounters/balance", json=payload)
    assert resp.status_code == 200
    data = resp.json()

    assert "encounter_id" in data
    assert data["party_size"] == 4
    assert data["target_difficulty"] == "Medium"

    thresholds = data["total_party_xp_threshold"]
    assert thresholds["easy"] == 300
    assert thresholds["medium"] == 600
    assert thresholds["hard"] == 900
    assert thresholds["deadly"] == 1600

    assert len(data["monsters"]) >= 1
    rec = data["monsters"][0]
    for key in ("name", "cr", "xp", "count", "role", "subtotal_xp"):
        assert key in rec

    assert data["adjusted_xp"] > 0
    assert data["multiplier"] >= 1.0
    assert "tactical_summary" in data


def test_encounter_builder_component_and_styles() -> None:
    """Verify encounter builder custom element and modular styles per TASK-0185."""
    ui_dir = REPO_ROOT / "services/rules_compendium/ui"
    enc_file = ui_dir / "src/runefoble-encounter-builder.ts"
    assert enc_file.is_file()
    enc_src = enc_file.read_text(encoding="utf-8")
    assert "@customElement('runefoble-encounter-builder')" in enc_src

    styles_file = ui_dir / "src/styles/encounter-builder.styles.ts"
    assert styles_file.is_file()
    assert len(styles_file.read_text(encoding="utf-8").splitlines()) < 120
    assert "export const encounterBuilderStyles" in styles_file.read_text(encoding="utf-8")


def test_compendium_package_and_stories() -> None:
    """Verify UI package configuration, exports, and Storybook stories."""
    ui_dir = REPO_ROOT / "services/rules_compendium/ui"
    pkg_json = json.loads((ui_dir / "package.json").read_text(encoding="utf-8"))
    assert pkg_json["name"] == "@runefoble/rules-compendium-ui"
    assert "./runefoble-encounter-builder" in pkg_json["exports"]
    assert "./runefoble-homebrew-creator" in pkg_json["exports"]
    assert "./runefoble-rules-lookup" in pkg_json["exports"]
    assert (ui_dir / "tsconfig.json").is_file()
    assert (ui_dir / "src/styles/index.ts").is_file()

    stories = (ui_dir / "src/runefoble-rules-compendium.stories.ts").read_text(encoding="utf-8")
    assert "Default" in stories
    assert "SearchResultsWithLatency" in stories
    assert "MonsterStatCards" in stories
    assert "CREncounterBalanceCalculator" in stories
