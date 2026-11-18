"""Core attributes, vitals, and model facade invariant tests."""

from __future__ import annotations

import character_sheet.models as models_facade
from character_sheet.models import (
    AddWardrobeVariantRequest,
    AssignCampaignRequest,
    AttributeScores,
    CharacterCore,
    CharacterSheetState,
    CharacterState,
    CreateCharacterRequest,
    HealthChangeRequest,
    PortraitResponse,
    SetActivePortraitRequest,
    VitalsTransitionsMixin,
    WardrobeVariant,
)
from character_sheet.models.base import AttributeScores as BaseAttributeScores
from character_sheet.models.base import VitalsTransitionsMixin as BaseVitalsTransitionsMixin
from character_sheet.models.base import WardrobeVariant as BaseWardrobeVariant
from character_sheet.models.character import AttributeScores as CharAttributeScores
from character_sheet.models.character import CharacterCore as CharCharacterCore
from character_sheet.models.character import CharacterSheetState as CharCharacterSheetState
from character_sheet.models.character import CharacterState as CharCharacterState


def test_core_facade_and_direct_imports() -> None:
    """Verify core models, mixins, and schemas are importable and aliased correctly."""
    assert models_facade is not None
    assert CharacterState is CharCharacterState and CharacterSheetState is CharacterState
    assert CharCharacterSheetState is CharacterSheetState
    assert CharacterCore is CharCharacterCore
    assert AttributeScores is CharAttributeScores is BaseAttributeScores
    assert WardrobeVariant is BaseWardrobeVariant
    assert VitalsTransitionsMixin is BaseVitalsTransitionsMixin
    assert CreateCharacterRequest is not None
    assert HealthChangeRequest is not None
    assert AssignCampaignRequest is not None
    assert AddWardrobeVariantRequest is not None
    assert SetActivePortraitRequest is not None
    assert PortraitResponse is not None


def test_attribute_scores_and_serialization() -> None:
    """Verify AttributeScores property access and serialization."""
    scores = AttributeScores(str=16, dex=14, con=15, intelligence=12, wis=10, cha=8)
    assert scores.str == 16 and scores.int == 12
    dict_scores = scores.to_dict()
    assert dict_scores["str"] == 16 and dict_scores["int"] == 12


def test_vitals_health_transitions_and_guardrails(sample_character_state: CharacterState) -> None:
    """Verify health mutations, stand-in guardrails, and unconscious stabilization."""
    damaged = sample_character_state.with_health(25)
    assert sample_character_state.current_hp == 40
    assert damaged.current_hp == 25

    guardrails = damaged.with_stand_in_guardrails(
        {"avoid_melee": False, "risk_threshold": "reckless"}
    )
    assert guardrails.stand_in_guardrails.risk_threshold == "reckless"

    stabilized = damaged.with_stabilized()
    assert stabilized.current_hp == 0 and stabilized.is_stabilized is True
    assert "unconscious_stabilized" in stabilized.conditions
