"""Pydantic state schemas, domain models, and API requests for Character Sheet."""

from __future__ import annotations

from character_sheet.models.base import StandInGuardrails, VitalsTransitionsMixin, WardrobeVariant
from character_sheet.models.character import (
    AttributeScores,
    CharacterCore,
    CharacterSheetState,
    CharacterState,
)
from character_sheet.models.conditions import (
    ConditionModifier,
    ConditionState,
    ConditionsTransitionsMixin,
)
from character_sheet.models.inventory import (
    Encumbrance,
    EquipmentSlot,
    InventoryItem,
    InventoryTransitionsMixin,
)
from character_sheet.models.progression import (
    LevelProgression,
    ProgressionTransitionsMixin,
    SpellProgression,
)
from character_sheet.schemas import (
    AddInventoryItemRequest,
    AddWardrobeVariantRequest,
    ApplyConditionRequest,
    AssignCampaignRequest,
    CastSpellRequest,
    CreateCharacterRequest,
    EquipItemRequest,
    HealthChangeRequest,
    LevelUpRequest,
    PenaltyRequest,
    PortraitResponse,
    PrepareSpellRequest,
    RemoveInventoryItemRequest,
    SetActivePortraitRequest,
    UpdateGuardrailsRequest,
)

__all__ = [
    "AddInventoryItemRequest",
    "AddWardrobeVariantRequest",
    "ApplyConditionRequest",
    "AssignCampaignRequest",
    "AttributeScores",
    "CastSpellRequest",
    "CharacterCore",
    "CharacterSheetState",
    "CharacterState",
    "ConditionModifier",
    "ConditionState",
    "ConditionsTransitionsMixin",
    "CreateCharacterRequest",
    "Encumbrance",
    "EquipmentSlot",
    "EquipItemRequest",
    "HealthChangeRequest",
    "InventoryItem",
    "InventoryTransitionsMixin",
    "LevelProgression",
    "LevelUpRequest",
    "PenaltyRequest",
    "PortraitResponse",
    "PrepareSpellRequest",
    "ProgressionTransitionsMixin",
    "RemoveInventoryItemRequest",
    "SetActivePortraitRequest",
    "SpellProgression",
    "StandInGuardrails",
    "UpdateGuardrailsRequest",
    "VitalsTransitionsMixin",
    "WardrobeVariant",
]
