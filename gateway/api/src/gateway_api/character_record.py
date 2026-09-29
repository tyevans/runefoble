"""Character domain record dataclass with dual-case serialization."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from gateway_api.character_defaults import (
    DEFAULT_RECORD_EQUIPMENT,
    DEFAULT_RECORD_GUARDRAILS,
    DEFAULT_RECORD_INVENTORY,
)
from gateway_api.character_models import CharacterResponse


@dataclass
class CharacterRecord:
    id: str
    name: str
    character_class: str
    subclass: str | None = None
    level: int = 1
    current_hp: int = 10
    max_hp: int = 10
    armor_class: int = 10
    speed: int = 30
    campaign_id: str | None = None
    owner_id: str = ""
    portrait_url: str | None = None
    equipment: dict[str, Any] = field(default_factory=lambda: dict(DEFAULT_RECORD_EQUIPMENT))
    inventory: dict[str, Any] = field(default_factory=lambda: dict(DEFAULT_RECORD_INVENTORY))
    conditions: dict[str, Any] = field(default_factory=dict)
    penalties: dict[str, str] = field(default_factory=dict)
    spell_slots: dict[int, int] = field(default_factory=lambda: {1: 4, 2: 2})
    max_spell_slots: dict[int, int] = field(default_factory=lambda: {1: 4, 2: 2})
    prepared_spells: list[str] = field(default_factory=lambda: ["Magic Missile", "Shield"])
    spellbook: list[str] = field(
        default_factory=lambda: ["Magic Missile", "Shield", "Detect Magic", "Misty Step"]
    )
    stand_in_guardrails: dict[str, Any] = field(
        default_factory=lambda: dict(DEFAULT_RECORD_GUARDRAILS)
    )
    is_stand_in_active: bool = False
    is_stabilized: bool = False

    def to_dict(self, campaign_title: str | None = None) -> dict[str, Any]:
        title = campaign_title
        if title is None and self.campaign_id:
            try:
                from gateway_api.campaign_store import campaign_store

                c = campaign_store.get_campaign(self.campaign_id)
                title = c.title if c else f"Campaign #{self.campaign_id}"
            except Exception:
                title = f"Campaign #{self.campaign_id}"

        return {
            "id": self.id,
            "name": self.name,
            "character_class": self.character_class,
            "subclass": self.subclass,
            "level": self.level,
            "current_hp": self.current_hp,
            "max_hp": self.max_hp,
            "armor_class": self.armor_class,
            "speed": self.speed,
            "campaign_id": self.campaign_id,
            "campaign_title": title,
            "owner_id": self.owner_id,
            "portrait_url": self.portrait_url,
            "equipment": dict(self.equipment),
            "inventory": dict(self.inventory),
            "conditions": dict(self.conditions),
            "penalties": dict(self.penalties),
            "spell_slots": dict(self.spell_slots),
            "max_spell_slots": dict(self.max_spell_slots),
            "prepared_spells": list(self.prepared_spells),
            "spellbook": list(self.spellbook),
            "stand_in_guardrails": dict(self.stand_in_guardrails),
            "is_stand_in_active": self.is_stand_in_active,
            "is_stabilized": self.is_stabilized,
            "characterClass": self.character_class,
            "currentHp": self.current_hp,
            "maxHp": self.max_hp,
            "armorClass": self.armor_class,
            "campaignId": self.campaign_id,
            "campaignTitle": title,
            "ownerId": self.owner_id,
            "portraitUrl": self.portrait_url,
            "spellSlots": dict(self.spell_slots),
            "maxSpellSlots": dict(self.max_spell_slots),
            "preparedSpells": list(self.prepared_spells),
            "standInGuardrails": dict(self.stand_in_guardrails),
            "isAiStandIn": self.is_stand_in_active,
            "isStabilized": self.is_stabilized,
        }

    def to_response(self, campaign_title: str | None = None) -> CharacterResponse:
        return CharacterResponse(**self.to_dict(campaign_title=campaign_title))
