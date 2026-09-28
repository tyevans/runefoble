"""Base traits, attribute scores, wardrobe variants, and stand-in guardrails."""

from __future__ import annotations

from typing import Any, Literal

from character_sheet.portrait import compute_condition_badges, resolve_active_portrait_url
from pydantic import BaseModel, Field

DEFAULT_SCORES: dict[str, int] = dict.fromkeys(["str", "dex", "con", "int", "wis", "cha"], 10)


class AttributeScores(BaseModel):
    model_config = {"populate_by_name": True}
    str: int = 10
    dex: int = 10
    con: int = 10
    intelligence: int = Field(default=10, alias="int")
    wis: int = 10
    cha: int = 10

    def __getattr__(self, name: str) -> Any:
        if name == "int":
            return self.intelligence
        raise AttributeError(f"{type(self).__name__!r} object has no attribute {name!r}")

    def to_dict(self) -> dict[str, int]:
        return self.model_dump(by_alias=True)


class WardrobeVariant(BaseModel):
    variant_id: str
    variant_name: str
    attire_type: str = "base"
    image_url: str
    prompt: str = ""
    created_at: str = ""


class StandInGuardrails(BaseModel):
    preserve_spell_slots: dict[int, int] = Field(default_factory=dict)
    protect_allies: list[str] = Field(default_factory=list)
    protect_ally_hp_threshold: float = 0.3
    risk_threshold: Literal["cautious", "balanced", "reckless"] = "cautious"
    avoid_melee: bool = True
    permadeath_safeguard: bool = True
    custom_priorities: list[str] = Field(default_factory=list)


class VitalsTransitionsMixin:
    """Transition methods for core character vitals, portraits, and stand-in policies."""

    def with_campaign(self: Any, campaign_id: str | None) -> Any:
        return self.model_copy(update={"campaign_id": campaign_id})

    def with_core_attributes(
        self: Any,
        *,
        subclass: str | None = None,
        armor_class: int | None = None,
        speed_ft: int | None = None,
        ability_scores: dict[str, int] | None = None,
    ) -> Any:
        raw = {
            "subclass": subclass,
            "armor_class": armor_class,
            "speed_ft": speed_ft,
            "ability_scores": ability_scores,
        }
        return self.model_copy(update={k: v for k, v in raw.items() if v is not None})

    def with_health(self: Any, current_hp: int) -> Any:
        badges = compute_condition_badges(current_hp, self.max_hp, self.conditions)
        active_url = resolve_active_portrait_url(
            self.base_portrait_url, current_hp, self.max_hp, self.conditions
        )
        return self.model_copy(
            update={
                "current_hp": current_hp,
                "condition_badges": badges,
                "active_portrait_url": active_url,
            }
        )

    def with_wardrobe_variant(self: Any, variant: WardrobeVariant) -> Any:
        return self.model_copy(
            update={"wardrobe_variants": {**self.wardrobe_variants, variant.variant_id: variant}}
        )

    def with_active_portrait(
        self: Any, variant_id: str | None, custom_url: str | None = None
    ) -> Any:
        new_base = (
            self.wardrobe_variants[variant_id].image_url
            if variant_id and variant_id in self.wardrobe_variants
            else (custom_url or self.base_portrait_url)
        )
        active_url = resolve_active_portrait_url(
            new_base, self.current_hp, self.max_hp, self.conditions
        )
        return self.model_copy(
            update={
                "active_variant_id": variant_id,
                "base_portrait_url": new_base,
                "active_portrait_url": active_url,
            }
        )

    def with_stand_in_guardrails(self: Any, guardrails: StandInGuardrails | dict[str, Any]) -> Any:
        gr = (
            StandInGuardrails.model_validate(guardrails)
            if isinstance(guardrails, dict)
            else guardrails
        )
        return self.model_copy(update={"stand_in_guardrails": gr})

    def with_stand_in_active(self: Any, active: bool) -> Any:
        return self.model_copy(update={"is_stand_in_active": active})
