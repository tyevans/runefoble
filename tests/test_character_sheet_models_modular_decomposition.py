"""Tests verifying modular decomposition and backward compatibility of character_sheet models.

Governed by:
- ADR-0003: UV Monorepo Workspace for Python BCs
- ADR-0007: Domain-Driven Design Architecture
- Hard Invariant 6: File length limit (< 500 lines, target < 120 lines per model submodule)
- Hard Invariant 7: Blackbox TDD with Frontdoor Setup
"""

from __future__ import annotations

from pathlib import Path
from uuid import uuid4

import character_sheet.models as models_facade
from character_sheet.main import app
from character_sheet.models import (
    AddInventoryItemRequest,
    AddWardrobeVariantRequest,
    ApplyConditionRequest,
    AssignCampaignRequest,
    AttributeScores,
    CastSpellRequest,
    CharacterCore,
    CharacterSheetState,
    CharacterState,
    ConditionModifier,
    ConditionState,
    ConditionsTransitionsMixin,
    CreateCharacterRequest,
    Encumbrance,
    EquipItemRequest,
    EquipmentSlot,
    HealthChangeRequest,
    InventoryItem,
    InventoryTransitionsMixin,
    LevelProgression,
    LevelUpRequest,
    PenaltyRequest,
    PortraitResponse,
    PrepareSpellRequest,
    ProgressionTransitionsMixin,
    RemoveInventoryItemRequest,
    SetActivePortraitRequest,
    SpellProgression,
    StandInGuardrails,
    UpdateGuardrailsRequest,
    VitalsTransitionsMixin,
    WardrobeVariant,
)
from character_sheet.models.base import (
    AttributeScores as BaseAttributeScores,
)
from character_sheet.models.base import (
    StandInGuardrails as BaseStandInGuardrails,
)
from character_sheet.models.base import (
    VitalsTransitionsMixin as BaseVitalsTransitionsMixin,
)
from character_sheet.models.base import (
    WardrobeVariant as BaseWardrobeVariant,
)
from character_sheet.models.character import (
    AttributeScores as CharAttributeScores,
)
from character_sheet.models.character import (
    CharacterCore as CharCharacterCore,
)
from character_sheet.models.character import (
    CharacterSheetState as CharCharacterSheetState,
)
from character_sheet.models.character import (
    CharacterState as CharCharacterState,
)
from character_sheet.models.conditions import (
    ConditionModifier as CondConditionModifier,
)
from character_sheet.models.conditions import (
    ConditionState as CondConditionState,
)
from character_sheet.models.conditions import (
    ConditionsTransitionsMixin as CondConditionsTransitionsMixin,
)
from character_sheet.models.inventory import (
    Encumbrance as InvEncumbrance,
)
from character_sheet.models.inventory import (
    EquipmentSlot as InvEquipmentSlot,
)
from character_sheet.models.inventory import (
    InventoryItem as InvInventoryItem,
)
from character_sheet.models.inventory import (
    InventoryTransitionsMixin as InvInventoryTransitionsMixin,
)
from character_sheet.models.progression import (
    LevelProgression as ProgLevelProgression,
)
from character_sheet.models.progression import (
    ProgressionTransitionsMixin as ProgProgressionTransitionsMixin,
)
from character_sheet.models.progression import (
    SpellProgression as ProgSpellProgression,
)
from fastapi.testclient import TestClient

REPO_ROOT = Path(__file__).resolve().parent.parent


def test_models_facade_and_submodules_line_length_invariants() -> None:
    """Verify models.py facade and all submodules strictly comply with line budget targets."""
    models_dir = REPO_ROOT / "services" / "character_sheet" / "src" / "character_sheet" / "models"
    facade_file = models_dir.parent / "models.py"

    assert facade_file.exists(), f"Facade file {facade_file} does not exist"
    facade_lines = len(facade_file.read_text(encoding="utf-8").splitlines())
    assert facade_lines < 40, f"Facade {facade_file} has {facade_lines} lines (expected < 40)"
    assert facade_lines < 30, f"Facade {facade_file} has {facade_lines} lines (expected < 30)"

    expected_submodules = {
        "character.py": 100,
        "inventory.py": 90,
        "conditions.py": 90,
        "progression.py": 90,
        "base.py": 120,
        "__init__.py": 120,
    }

    for sub_filename, max_lines in expected_submodules.items():
        sub_file = models_dir / sub_filename
        assert sub_file.exists(), f"Submodule file {sub_file} does not exist"
        lines = len(sub_file.read_text(encoding="utf-8").splitlines())
        assert lines < max_lines, (
            f"{sub_filename} has {lines} lines, exceeding strict limit of {max_lines}"
        )
        assert lines < 120, f"{sub_filename} has {lines} lines, exceeding Hard Invariant 6 limit"


def test_package_facade_and_backward_compatibility() -> None:
    """Verify that all domain models, schemas, and mixins are cleanly re-exported."""
    assert models_facade is not None
    assert CharacterState is not None
    assert CharacterSheetState is CharacterState
    assert CharacterCore is not None
    assert AttributeScores is not None
    assert InventoryItem is not None
    assert EquipmentSlot is not None
    assert Encumbrance is not None
    assert ConditionState is not None
    assert ConditionModifier is not None
    assert WardrobeVariant is not None
    assert StandInGuardrails is not None
    assert SpellProgression is not None
    assert LevelProgression is not None

    # Mixins
    assert InventoryTransitionsMixin is not None
    assert ConditionsTransitionsMixin is not None
    assert ProgressionTransitionsMixin is not None
    assert VitalsTransitionsMixin is not None

    # Re-exported request and response schemas
    assert AddInventoryItemRequest is not None
    assert AddWardrobeVariantRequest is not None
    assert ApplyConditionRequest is not None
    assert AssignCampaignRequest is not None
    assert CastSpellRequest is not None
    assert CreateCharacterRequest is not None
    assert EquipItemRequest is not None
    assert HealthChangeRequest is not None
    assert LevelUpRequest is not None
    assert PenaltyRequest is not None
    assert PortraitResponse is not None
    assert PrepareSpellRequest is not None
    assert RemoveInventoryItemRequest is not None
    assert SetActivePortraitRequest is not None
    assert UpdateGuardrailsRequest is not None


def test_submodule_direct_imports() -> None:
    """Verify that models are directly importable from domain submodules."""
    assert CharCharacterCore is CharacterCore
    assert CharCharacterState is CharacterState
    assert CharCharacterSheetState is CharacterSheetState
    assert CharAttributeScores is AttributeScores
    assert BaseAttributeScores is AttributeScores

    assert InvInventoryItem is InventoryItem
    assert InvEquipmentSlot is EquipmentSlot
    assert InvEncumbrance is Encumbrance
    assert InvInventoryTransitionsMixin is InventoryTransitionsMixin

    assert CondConditionState is ConditionState
    assert CondConditionModifier is ConditionModifier
    assert CondConditionsTransitionsMixin is ConditionsTransitionsMixin

    assert ProgSpellProgression is SpellProgression
    assert ProgLevelProgression is LevelProgression
    assert ProgProgressionTransitionsMixin is ProgressionTransitionsMixin

    assert BaseWardrobeVariant is WardrobeVariant
    assert BaseStandInGuardrails is StandInGuardrails
    assert BaseVitalsTransitionsMixin is VitalsTransitionsMixin


def test_attribute_scores_and_encumbrance_mechanics() -> None:
    """Verify AttributeScores property access and dynamic Encumbrance tier calculations."""
    scores = AttributeScores(str=16, dex=14, con=15, intelligence=12, wis=10, cha=8)
    assert scores.str == 16
    assert scores.int == 12
    dict_scores = scores.to_dict()
    assert dict_scores["str"] == 16
    assert dict_scores["int"] == 12

    # Encumbrance calculations per docs/how-to/interact-with-character-sheet-and-inventory.md
    # Strength = 10 -> capacity = 150 lbs
    # Light: <= 33% (<= 49.5 lbs)
    # Medium: <= 66% (<= 99.0 lbs)
    # Heavy: <= 100% (<= 150.0 lbs)
    # Overburdened: > 100% (> 150.0 lbs)

    light_items = [InventoryItem(item_id="i1", name="Rations", quantity=10, weight_lbs=2.0)]
    enc_light = Encumbrance.calculate(light_items, strength=10)
    assert enc_light.tier == "light"
    assert enc_light.current_weight_lbs == 20.0
    assert enc_light.capacity_lbs == 150.0

    med_items = [InventoryItem(item_id="i2", name="Chain Mail", quantity=1, weight_lbs=55.0)]
    enc_med = Encumbrance.calculate(med_items, strength=10)
    assert enc_med.tier == "medium"
    assert enc_med.current_weight_lbs == 55.0

    heavy_items = [
        InventoryItem(item_id="i2", name="Chain Mail", quantity=1, weight_lbs=55.0),
        InventoryItem(item_id="i3", name="Anvil", quantity=1, weight_lbs=60.0),
    ]
    enc_heavy = Encumbrance.calculate(heavy_items, strength=10)
    assert enc_heavy.tier == "heavy"
    assert enc_heavy.current_weight_lbs == 115.0

    over_items = [InventoryItem(item_id="i4", name="Massive Boulder", quantity=1, weight_lbs=180.0)]
    enc_over = Encumbrance.calculate(over_items, strength=10)
    assert enc_over.tier == "overburdened"
    assert enc_over.current_weight_lbs == 180.0


def test_character_state_transitions_and_immutability() -> None:
    """Verify CharacterState transitions produce immutable valid domain copies."""
    char_id = uuid4()
    initial_state = CharacterState.initial(
        character_id=char_id,
        name="Thorne Ironfoot",
        character_class="Paladin",
        max_hp=40,
        current_hp=40,
        player_id="player-thorn",
        personality_traits=["resolute", "just"],
        campaign_id="camp-101",
        subclass="Oath of the Ancients",
        armor_class=18,
        speed_ft=30,
        ability_scores={"str": 16, "dex": 10, "con": 14, "int": 10, "wis": 12, "cha": 14},
    )

    assert initial_state.name == "Thorne Ironfoot"
    assert initial_state.current_hp == 40
    assert initial_state.level == 1
    assert initial_state.armor_class == 18

    # 1. Health mutation
    damaged_state = initial_state.with_health(25)
    assert initial_state.current_hp == 40
    assert damaged_state.current_hp == 25

    # 2. Inventory and equipment mutations
    with_item_state = damaged_state.with_inventory_item(
        item_id="item-greatsword", name="Greatsword", quantity=1, weight_lbs=6.0
    )
    assert "item-greatsword" in with_item_state.inventory
    assert with_item_state.inventory["item-greatsword"].quantity == 1

    equipped_state = with_item_state.with_equipment_slot("main_hand", "Greatsword")
    assert equipped_state.equipment["main_hand"] == "Greatsword"

    unequipped_state = equipped_state.with_equipment_slot("main_hand", None)
    assert "main_hand" not in unequipped_state.equipment

    removed_item_state = unequipped_state.without_inventory_item("item-greatsword", 1)
    assert "item-greatsword" not in removed_item_state.inventory

    # 3. Conditions and penalties
    cond_state = damaged_state.with_condition("blinded", duration_rounds=3, source="flashbang")
    assert "blinded" in cond_state.conditions
    assert cond_state.conditions["blinded"].duration_rounds == 3

    uncond_state = cond_state.without_condition("blinded")
    assert "blinded" not in uncond_state.conditions

    pen_state = damaged_state.with_penalty("drunk", "DM imposed drunkenness penalty")
    assert "drunk" in pen_state.penalties
    unpen_state = pen_state.without_penalty("drunk")
    assert "drunk" not in unpen_state.penalties

    # 4. Level up and spells
    level_state = damaged_state.with_level_up(2, max_hp_increase=10, spell_slots={1: 3})
    assert level_state.level == 2
    assert level_state.max_hp == 50
    assert level_state.current_hp == 35
    assert level_state.spell_slots == {1: 3}

    spell_state = level_state.with_prepared_spell("Cure Wounds")
    assert "Cure Wounds" in spell_state.prepared_spells
    assert "Cure Wounds" in spell_state.spellbook

    expended_state = spell_state.with_expended_spell_slot(1, 2)
    assert expended_state.spell_slots[1] == 2

    # 5. Stand-in and stabilization
    guardrails_state = damaged_state.with_stand_in_guardrails(
        {"avoid_melee": False, "risk_threshold": "reckless"}
    )
    assert guardrails_state.stand_in_guardrails.risk_threshold == "reckless"

    stabilized_state = damaged_state.with_stabilized()
    assert stabilized_state.current_hp == 0
    assert stabilized_state.is_stabilized is True
    assert "unconscious_stabilized" in stabilized_state.conditions


def test_frontdoor_character_sheet_api_with_models() -> None:
    """Verify public HTTP frontdoors handle models seamlessly without regressions."""
    client = TestClient(app)

    create_payload = {
        "name": "Eldrin Swift",
        "character_class": "Wizard",
        "max_hp": 22,
        "personality_traits": ["studious", "curious"],
        "armor_class": 12,
        "speed_ft": 30,
        "ability_scores": {"str": 8, "dex": 14, "con": 12, "int": 17, "wis": 13, "cha": 10},
    }
    create_res = client.post("/api/v1/characters", json=create_payload)
    assert create_res.status_code == 200, create_res.text
    char_data = create_res.json()
    char_id = char_data["character_id"]
    assert char_data["name"] == "Eldrin Swift"
    assert char_data["level"] == 1
    assert char_data["ability_scores"]["int"] == 17

    # Add item frontdoor
    add_item_res = client.post(
        f"/api/v1/characters/{char_id}/inventory/add",
        json={"item_id": "it-wand-1", "name": "Wand of Sparks", "quantity": 1, "weight_lbs": 1.0},
    )
    assert add_item_res.status_code == 200
    assert "it-wand-1" in add_item_res.json()["inventory"]

    # Equip item frontdoor
    equip_res = client.post(
        f"/api/v1/characters/{char_id}/equipment",
        json={"slot": "main_hand", "item_name": "Wand of Sparks"},
    )
    assert equip_res.status_code == 200
    assert equip_res.json()["equipment"]["main_hand"] == "Wand of Sparks"

    # Apply condition frontdoor
    cond_res = client.post(
        f"/api/v1/characters/{char_id}/conditions",
        json={"condition": "poisoned", "duration_rounds": 2, "source": "viper"},
    )
    assert cond_res.status_code == 200
    assert "poisoned" in cond_res.json()["conditions"]

    # Level up frontdoor
    lvl_res = client.post(
        f"/api/v1/characters/{char_id}/level-up",
        json={"target_level": 2, "hp_increase": 6},
    )
    assert lvl_res.status_code == 200
    assert lvl_res.json()["level"] == 2
    assert lvl_res.json()["max_hp"] == 28

    # Prepare spell frontdoor
    prep_res = client.post(
        f"/api/v1/characters/{char_id}/spells/prepare",
        json={"spell_name": "Magic Missile", "spell_level": 1},
    )
    assert prep_res.status_code == 200
    assert "Magic Missile" in prep_res.json()["prepared_spells"]

    # Fetch character frontdoor
    get_res = client.get(f"/api/v1/characters/{char_id}")
    assert get_res.status_code == 200
    assert get_res.json()["character_id"] == char_id
