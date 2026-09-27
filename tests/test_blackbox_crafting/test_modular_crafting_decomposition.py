"""Frontdoor blackbox tests and modular decomposition verification for alchemical crafting.

Governed by:
- ADR-0003: UV Monorepo Workspace for Python BCs
- ADR-0007: Domain-Driven Design Architecture
- ADR-0011: eventsource-py Core Event Sourcing
- Hard Invariant 6: File length limit (< 500 lines per file; submodules strictly < 180 lines)
- Hard Invariant 7: Blackbox TDD with frontdoor setup
"""

from __future__ import annotations

from pathlib import Path
from uuid import uuid4

import pytest
from character_sheet.crafting import (
    CATALYSTS_CATALOGUE,
    KNOWN_RECIPES,
    MISHAP_TABLE,
    REAGENTS_CATALOGUE,
    CraftingAggregate,
    CraftingEngine,
    CraftingState,
    MishapResolver,
    Recipe,
    calculate_crafting_dc,
    calculate_volatile_risk,
    find_matching_recipe,
)
from character_sheet.crafting.engine import CraftingAggregate as EngineCraftingAggregate
from character_sheet.crafting.mishaps import MishapResolver as ModuleMishapResolver
from character_sheet.crafting.recipes import Recipe as ModuleRecipe
from character_sheet.dependencies import (
    STREAM_CRAFTING,
)
from character_sheet.dependencies import (
    set_event_bus as set_char_event_bus,
)
from character_sheet.main import app as character_app
from fastapi.testclient import TestClient
from runefoble_platform.mock_redis import MockAsyncRedis
from runefoble_platform.redis_bus import RedisStreamsEventBus

REPO_ROOT = Path(__file__).resolve().parent.parent.parent


@pytest.fixture
def mock_bus():
    redis_client = MockAsyncRedis()
    bus = RedisStreamsEventBus(client=redis_client)
    set_char_event_bus(bus)
    yield redis_client
    set_char_event_bus(None)


@pytest.fixture
def char_client():
    return TestClient(character_app)


def test_crafting_submodules_line_length_invariants():
    """Verify that crafting modules strictly adhere to file length limits."""
    crafting_dir = (
        REPO_ROOT / "services" / "character_sheet" / "src" / "character_sheet" / "crafting"
    )
    facade_file = crafting_dir.parent / "crafting.py"

    assert crafting_dir.is_dir(), "crafting package directory must exist"
    assert facade_file.is_file(), "crafting.py facade file must exist"

    recipes_file = crafting_dir / "recipes.py"
    mishaps_file = crafting_dir / "mishaps.py"
    engine_file = crafting_dir / "engine.py"
    init_file = crafting_dir / "__init__.py"

    for f in (recipes_file, mishaps_file, engine_file, init_file, facade_file):
        assert f.is_file(), f"{f.name} must exist"

    recipes_lines = len(recipes_file.read_text(encoding="utf-8").splitlines())
    mishaps_lines = len(mishaps_file.read_text(encoding="utf-8").splitlines())
    engine_lines = len(engine_file.read_text(encoding="utf-8").splitlines())
    init_lines = len(init_file.read_text(encoding="utf-8").splitlines())
    facade_lines = len(facade_file.read_text(encoding="utf-8").splitlines())

    assert recipes_lines < 120, f"recipes.py must be < 120 lines, got {recipes_lines}"
    assert mishaps_lines < 130, f"mishaps.py must be < 130 lines, got {mishaps_lines}"
    assert engine_lines < 130, f"engine.py must be < 130 lines, got {engine_lines}"
    assert init_lines < 30, f"__init__.py must be < 30 lines, got {init_lines}"
    assert facade_lines < 20, f"crafting.py facade must be < 20 lines, got {facade_lines}"

    for name, count in [
        ("recipes.py", recipes_lines),
        ("mishaps.py", mishaps_lines),
        ("engine.py", engine_lines),
        ("crafting.py", facade_lines),
    ]:
        assert count < 180, f"{name} must be strictly < 180 lines, got {count}"


def test_crafting_package_and_facade_exports():
    """Verify package re-exports and facade compatibility."""
    assert CraftingEngine is not None
    assert Recipe is ModuleRecipe
    assert MishapResolver is ModuleMishapResolver
    assert CraftingAggregate is EngineCraftingAggregate
    assert CraftingState is not None

    assert isinstance(REAGENTS_CATALOGUE, dict)
    assert isinstance(CATALYSTS_CATALOGUE, dict)
    assert isinstance(KNOWN_RECIPES, list)
    assert isinstance(MISHAP_TABLE, list)

    assert callable(calculate_volatile_risk)
    assert callable(calculate_crafting_dc)
    assert callable(find_matching_recipe)


def test_recipe_registry_and_difficulty_check():
    """Verify Recipe schema validation, matching, and DC calculations."""
    rec = Recipe(
        name="Sunfire Phial",
        ingredients={"Glowmoss Extract", "Wyrm Blood"},
        tags=["fire", "radiant"],
        description="Radiant flame concoction.",
        dc=14,
    )
    assert rec.name == "Sunfire Phial"
    assert rec.dc == 14

    matched = find_matching_recipe(["Glowmoss Extract", "Volcano Ash"])
    assert matched is not None
    assert matched["name"] == "Radiant Smoke Pellet"

    unmatched = find_matching_recipe(["Nonexistent Herb", "Star Lily"])
    assert unmatched is None

    dc = calculate_crafting_dc(["Glowmoss Extract", "Volcano Ash"], base_dc=10)
    assert dc == 15


def test_volatile_mishap_tables_and_resolution():
    """Verify d100 mishap tables, consequence resolvers, and risk scores."""
    assert len(MISHAP_TABLE) >= 4
    mishap_types = [m["mishap_type"] for m in MISHAP_TABLE]
    assert "minor_explosion" in mishap_types
    assert "caustic_fumes" in mishap_types
    assert "flashbang_stun" in mishap_types
    assert "bubbling_sludge" in mishap_types

    risk_water = calculate_volatile_risk(["Volcano Ash", "Wyrm Blood"], catalyst="purified_water")
    risk_raw = calculate_volatile_risk(["Volcano Ash", "Wyrm Blood"])
    assert risk_water < risk_raw

    assert MishapResolver.is_mishap(0.80, catalyst=None) is True
    assert MishapResolver.is_mishap(0.80, catalyst="purified_water") is False
    assert MishapResolver.is_mishap(0.20, force_mishap=True) is True

    selected_high = MishapResolver.select_mishap(0.75)
    assert selected_high["mishap_type"] == "minor_explosion"

    selected_d100 = MishapResolver.select_mishap(0.3, d100_roll=50)
    assert selected_d100["mishap_type"] in mishap_types

    ev = MishapResolver.create_mishap_event(
        character_id=uuid4(),
        mishap=selected_high,
        reagents=["Volcano Ash", "Wyrm Blood"],
    )
    assert ev.damage_dealt == 4
    assert ev.severity == "minor"


def test_crafting_engine_proficiency_and_resolution():
    """Verify CraftingEngine proficiency bonuses and recipe evaluation."""
    assert CraftingEngine.apply_proficiency(base=10, bonus=3) == 13

    item, recipe, tags, props = CraftingEngine.evaluate_recipe(
        ["Nightshade Berry", "Purified Quicksilver"]
    )
    assert item == "Serpent Venom Oil"
    assert "poison" in tags

    item_exp, recipe_exp, tags_exp, props_exp = CraftingEngine.evaluate_recipe(
        ["Star Lily", "Purified Quicksilver"]
    )
    assert "Experimental Brew" in item_exp
    assert recipe_exp == "Experimental Alchemy"
    assert "experimental" in tags_exp


def test_blackbox_crafting_frontdoor_api_success(char_client, mock_bus):
    """Test full alchemical crafting success flow through public HTTP frontdoors."""
    create_res = char_client.post(
        "/api/v1/characters",
        json={"name": "Artisan Bram", "character_class": "Artificer", "max_hp": 28},
    )
    assert create_res.status_code == 200
    char_id = create_res.json()["character_id"]

    char_client.post(
        f"/api/v1/characters/{char_id}/inventory/add",
        json={"name": "Glowmoss Extract", "quantity": 1, "weight_lbs": 0.2},
    )
    char_client.post(
        f"/api/v1/characters/{char_id}/inventory/add",
        json={"name": "Star Lily", "quantity": 1, "weight_lbs": 0.1},
    )

    combine_payload = {
        "character_id": char_id,
        "reagents": ["Glowmoss Extract", "Star Lily"],
        "catalyst": "purified_water",
    }
    res = char_client.post("/api/v1/crafting/recipes/combine", json=combine_payload)
    assert res.status_code == 200, res.text
    data = res.json()
    assert data["outcome"] == "success"
    assert data["item_name"] == "Elixir of Luminescence"
    assert "healing" in data["tags"]

    hist_res = char_client.get(f"/api/v1/crafting/{char_id}/history")
    assert hist_res.status_code == 200
    hist = hist_res.json()
    assert hist["total_crafts"] == 1
    assert hist["successful_crafts"] == 1
    assert "Elixir of Luminescence" in hist["discovered_recipes"]

    entries = mock_bus.streams.get(STREAM_CRAFTING, [])
    assert any("CraftingAttempted" in e[1].get("event_type", "") for e in entries)
    assert any("CraftingSucceeded" in e[1].get("event_type", "") for e in entries)


def test_blackbox_crafting_frontdoor_api_mishap(char_client, mock_bus):
    """Test volatile mishap flow through public HTTP frontdoors."""
    create_res = char_client.post(
        "/api/v1/characters",
        json={"name": "Reckless Apprentice", "character_class": "Sorcerer", "max_hp": 20},
    )
    assert create_res.status_code == 200
    char_id = create_res.json()["character_id"]
    initial_hp = create_res.json()["current_hp"]

    mishap_payload = {
        "character_id": char_id,
        "reagents": ["Volcano Ash", "Wyrm Blood"],
        "force_mishap": True,
    }
    res = char_client.post("/api/v1/crafting/recipes/combine", json=mishap_payload)
    assert res.status_code == 200
    data = res.json()
    assert data["outcome"] == "mishap"
    assert data["mishap"] is not None
    assert data["character_current_hp"] < initial_hp

    char_res = char_client.get(f"/api/v1/characters/{char_id}")
    assert char_res.json()["current_hp"] == data["character_current_hp"]

    entries = mock_bus.streams.get(STREAM_CRAFTING, [])
    assert any("CraftingMishapOccurred" in e[1].get("event_type", "") for e in entries)
