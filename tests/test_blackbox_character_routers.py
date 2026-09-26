"""Blackbox tests verifying modular APIRouter decomposition for character_sheet bounded context.

Ensures zero contract regressions, public HTTP frontdoor reachability, OpenAPI schema completeness,
and strict compliance with Hard Invariant 6 (file length < 500 lines) and task limits (< 180 lines).
"""

from pathlib import Path

import pytest
from character_sheet.main import app as character_app
from fastapi.testclient import TestClient

REPO_ROOT = Path(__file__).resolve().parent.parent


@pytest.fixture
def char_client():
    return TestClient(character_app)


def test_character_sheet_openapi_routes_completeness(char_client):
    """Verify that all decomposed APIRouter routes are registered in character_sheet OpenAPI schema."""
    openapi = char_client.app.openapi()
    paths = openapi["paths"]

    expected_routes = [
        "/healthz",
        "/ui/manifest",
        "/api/v1/characters",
        "/api/v1/characters/create",
        "/api/v1/characters/{character_id}",
        "/api/v1/characters/{character_id}/level-up",
        "/api/v1/characters/{character_id}/spells/prepare",
        "/api/v1/characters/{character_id}/spells/cast",
        "/api/v1/characters/{character_id}/health",
        "/api/v1/characters/{character_id}/penalties",
        "/api/v1/characters/{character_id}/penalties/{penalty_type}",
        "/api/v1/characters/{character_id}/inventory/add",
        "/api/v1/characters/{character_id}/inventory/{item_id}/remove",
        "/api/v1/characters/{character_id}/equipment",
        "/api/v1/characters/{character_id}/conditions",
        "/api/v1/characters/{character_id}/conditions/{condition}",
        "/api/v1/characters/{character_id}/guardrails",
    ]

    for route in expected_routes:
        assert route in paths, f"Route '{route}' missing from Character Sheet OpenAPI schema"


def test_character_sheet_lifecycle_and_spells_frontdoors(char_client):
    """Verify character creation, progression, and spellbook endpoints via public frontdoors."""
    # Health and UI manifest
    assert char_client.get("/healthz").status_code == 200
    assert char_client.get("/ui/manifest").status_code == 200

    # Create character
    create_res = char_client.post(
        "/api/v1/characters",
        json={"name": "Gale of Waterdeep", "character_class": "Wizard", "max_hp": 20},
    )
    assert create_res.status_code == 200
    data = create_res.json()
    char_id = data["character_id"]
    assert data["name"] == "Gale of Waterdeep"
    assert data["level"] == 1

    # Level up
    lvl_res = char_client.post(f"/api/v1/characters/{char_id}/level-up")
    assert lvl_res.status_code == 200
    assert lvl_res.json()["level"] == 2

    # Prepare spell
    prep_res = char_client.post(
        f"/api/v1/characters/{char_id}/spells/prepare",
        json={"spell_name": "Shield", "spell_level": 1},
    )
    assert prep_res.status_code == 200
    assert "Shield" in prep_res.json()["prepared_spells"]

    # Cast spell
    cast_res = char_client.post(
        f"/api/v1/characters/{char_id}/spells/cast",
        json={"spell_name": "Shield", "slot_level": 1},
    )
    assert cast_res.status_code == 200

    # Get character state
    get_res = char_client.get(f"/api/v1/characters/{char_id}")
    assert get_res.status_code == 200
    assert get_res.json()["character_id"] == char_id


def test_character_sheet_inventory_and_conditions_frontdoors(char_client):
    """Verify inventory, equipment, and condition lifecycle endpoints via public frontdoors."""
    create_res = char_client.post(
        "/api/v1/characters/create",
        json={"name": "Shadowheart", "character_class": "Cleric", "max_hp": 24},
    )
    assert create_res.status_code == 200
    char_id = create_res.json()["character_id"]

    # Add inventory item
    inv_res = char_client.post(
        f"/api/v1/characters/{char_id}/inventory/add",
        json={"item_id": "mace-1", "name": "Mace of Disruption", "quantity": 1, "weight_lbs": 4.0},
    )
    assert inv_res.status_code == 200
    assert "mace-1" in inv_res.json()["inventory"]

    # Equip item
    eq_res = char_client.post(
        f"/api/v1/characters/{char_id}/equipment",
        json={"slot": "main_hand", "item_name": "Mace of Disruption"},
    )
    assert eq_res.status_code == 200
    assert eq_res.json()["equipment"]["main_hand"] == "Mace of Disruption"

    # Remove inventory item
    rem_inv_res = char_client.post(
        f"/api/v1/characters/{char_id}/inventory/mace-1/remove",
        json={"quantity": 1},
    )
    assert rem_inv_res.status_code == 200
    assert "mace-1" not in rem_inv_res.json()["inventory"]

    # Apply condition
    cond_res = char_client.post(
        f"/api/v1/characters/{char_id}/conditions",
        json={"condition": "blessed", "duration_rounds": 10, "source": "Bless spell"},
    )
    assert cond_res.status_code == 200
    assert "blessed" in cond_res.json()["conditions"]

    # Remove condition
    del_cond_res = char_client.delete(f"/api/v1/characters/{char_id}/conditions/blessed")
    assert del_cond_res.status_code == 200
    assert "blessed" not in del_cond_res.json()["conditions"]


def test_character_sheet_penalties_and_guardrails_frontdoors(char_client):
    """Verify penalties, health modification, and stand-in guardrails via public frontdoors."""
    create_res = char_client.post(
        "/api/v1/characters",
        json={"name": "Astarion", "character_class": "Rogue", "max_hp": 28},
    )
    assert create_res.status_code == 200
    cid = create_res.json()["character_id"]

    # Apply penalty
    pen_res = char_client.post(
        f"/api/v1/characters/{cid}/penalties",
        json={"penalty_type": "drunk", "description": "Too much elven wine"},
    )
    assert pen_res.status_code == 200
    assert "drunk" in pen_res.json()["penalties"]

    # Clear penalty
    clear_pen_res = char_client.delete(f"/api/v1/characters/{cid}/penalties/drunk")
    assert clear_pen_res.status_code == 200
    assert "drunk" not in clear_pen_res.json()["penalties"]

    # Health modification
    hp_res = char_client.post(
        f"/api/v1/characters/{cid}/health",
        json={"delta": -10, "source": "Trap"},
    )
    assert hp_res.status_code == 200
    assert hp_res.json()["current_hp"] == 18

    # Stand-in guardrails update & get
    guard_res = char_client.put(
        f"/api/v1/characters/{cid}/guardrails",
        json={
            "risk_threshold": "cautious",
            "avoid_melee": True,
            "preserve_spell_slots": {"1": 1},
        },
    )
    assert guard_res.status_code == 200
    assert guard_res.json()["stand_in_guardrails"]["risk_threshold"] == "cautious"

    get_guard_res = char_client.get(f"/api/v1/characters/{cid}/guardrails")
    assert get_guard_res.status_code == 200
    assert get_guard_res.json()["risk_threshold"] == "cautious"


def test_character_sheet_modular_file_invariants():
    """Verify strict adherence to line length limits across decomposed character_sheet modules."""
    cs_dir = REPO_ROOT / "services" / "character_sheet" / "src" / "character_sheet"

    # Specific file limits under TASK-0077 DoD
    main_py = cs_dir / "main.py"
    router_py = cs_dir / "router.py"
    schemas_py = cs_dir / "schemas.py"

    assert main_py.exists()
    assert router_py.exists()
    assert schemas_py.exists()

    main_lines = len(main_py.read_text().splitlines())
    router_lines = len(router_py.read_text().splitlines())
    schemas_lines = len(schemas_py.read_text().splitlines())

    assert main_lines < 180, (
        f"main.py exceeds 180 lines limit under TASK-0077 (current: {main_lines})"
    )
    assert router_lines < 180, (
        f"router.py exceeds 180 lines limit under TASK-0077 (current: {router_lines})"
    )
    assert schemas_lines < 180, (
        f"schemas.py exceeds 180 lines limit under TASK-0077 (current: {schemas_lines})"
    )

    # Hard Invariant 6: All python source files must be strictly under 500 lines
    for py_file in cs_dir.glob("*.py"):
        line_count = len(py_file.read_text().splitlines())
        assert line_count < 500, (
            f"File {py_file.name} violates Hard Invariant 6 with {line_count} lines (>500 limit)"
        )
