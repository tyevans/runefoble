"""Alchemical crafting engine, reagent affinities, and volatile risk tables.

Part of TASK-0100 / PRD-0014 / US-0044: Interactive campfire downtime and crafting.
Governed by Hard Invariant 2: State changes flow strictly through DeclarativeAggregate.
"""

from __future__ import annotations

from typing import Any
from uuid import UUID

from eventsource.domain.aggregate import DeclarativeAggregate
from eventsource.domain.decorators import handles
from pydantic import BaseModel, Field
from runefoble_events.events import (
    CraftingAttempted,
    CraftingMishapOccurred,
    CraftingSucceeded,
)

# Reagent Catalogue
REAGENTS_CATALOGUE: dict[str, dict[str, Any]] = {
    "Glowmoss Extract": {
        "affinity": "radiant",
        "secondary_affinity": "botanical",
        "instability": 0.10,
        "potency": 2,
        "description": "Phosphorescent cave moss distilled into an illuminating azure fluid.",
    },
    "Volcano Ash": {
        "affinity": "volatile",
        "secondary_affinity": "mineral",
        "instability": 0.35,
        "potency": 3,
        "description": "Sulfuric volcanic powder containing dormant thermal energy.",
    },
    "Star Lily": {
        "affinity": "radiant",
        "secondary_affinity": "botanical",
        "instability": 0.05,
        "potency": 2,
        "description": "A rare mountain flower that blooms exclusively under starlight.",
    },
    "Wyrm Blood": {
        "affinity": "draconic",
        "secondary_affinity": "volatile",
        "instability": 0.40,
        "potency": 4,
        "description": "Thick crimson dragon blood radiating innate magical heat.",
    },
    "Nightshade Berry": {
        "affinity": "toxic",
        "secondary_affinity": "botanical",
        "instability": 0.30,
        "potency": 2,
        "description": "Potent forest berries rich in paralyzing alkaloids.",
    },
    "Purified Quicksilver": {
        "affinity": "arcane",
        "secondary_affinity": "mineral",
        "instability": 0.20,
        "potency": 3,
        "description": "Alchemically stabilized liquid silver, an exceptional magical conduit.",
    },
    "Frost Lichen": {
        "affinity": "aqueous",
        "secondary_affinity": "botanical",
        "instability": 0.15,
        "potency": 2,
        "description": "Glacial tundra lichen that freezes ambient moisture upon touch.",
    },
}

CATALYSTS_CATALOGUE: dict[str, dict[str, Any]] = {
    "purified_water": {
        "stability_bonus": -0.20,
        "potency_mod": 0,
        "description": "Neutral distilled spring water that dampens volatile thermal reactions.",
    },
    "dragon_bile": {
        "stability_bonus": 0.15,
        "potency_mod": 2,
        "description": "Hyper-reactive enzymatic fluid that supercharges potion potency.",
    },
    "quicksilver": {
        "stability_bonus": -0.15,
        "potency_mod": 1,
        "description": "Fluid metal catalyst that binds mineral reagents cleanly.",
    },
    "spirit_ash": {
        "stability_bonus": -0.25,
        "potency_mod": 0,
        "description": "Blessed ceremonial ash that quells radiant and necrotic volatility.",
    },
}

KNOWN_RECIPES: list[dict[str, Any]] = [
    {
        "name": "Radiant Smoke Pellet",
        "ingredients": {"Glowmoss Extract", "Volcano Ash"},
        "tags": ["consumable", "radiant", "obscurement", "aoe"],
        "description": "A shimmering sphere that bursts into brilliant illuminating smoke on impact.",
        "properties": {"radius_ft": 20, "duration_rounds": 3, "save_type": "none"},
    },
    {
        "name": "Elixir of Luminescence",
        "ingredients": {"Glowmoss Extract", "Star Lily"},
        "tags": ["potion", "radiant", "healing"],
        "description": "Restores 2d4+2 HP and sheds 20ft bright light for 1 hour.",
        "properties": {"heal_dice": "2d4+2", "light_radius_ft": 20, "duration_hours": 1},
    },
    {
        "name": "Liquid Hellfire",
        "ingredients": {"Volcano Ash", "Wyrm Blood"},
        "tags": ["oil", "fire", "destructive"],
        "description": "Coats weapon for +1d6 fire damage for 1 minute.",
        "properties": {"bonus_damage": "1d6 fire", "duration_minutes": 1},
    },
    {
        "name": "Serpent Venom Oil",
        "ingredients": {"Nightshade Berry", "Purified Quicksilver"},
        "tags": ["poison", "toxic", "weapon_coating"],
        "description": "Coats blade for 2d6 poison damage on the next hit.",
        "properties": {"save_dc": 13, "damage": "2d6 poison"},
    },
]

MISHAP_TABLE: list[dict[str, Any]] = [
    {
        "mishap_type": "minor_explosion",
        "severity": "minor",
        "damage": 4,
        "condition": None,
        "description": "A sharp bang fills the laboratory! Soot covers the crucible and singes eyebrows.",
    },
    {
        "mishap_type": "caustic_fumes",
        "severity": "moderate",
        "damage": 2,
        "condition": "poisoned",
        "description": "Acrid purple vapor spills forth, burning the lungs and inducing nausea.",
    },
    {
        "mishap_type": "flashbang_stun",
        "severity": "minor",
        "damage": 0,
        "condition": "blinded",
        "description": "A sudden blinding burst of light erupts from the crucible, dazzling vision.",
    },
    {
        "mishap_type": "bubbling_sludge",
        "severity": "minor",
        "damage": 0,
        "condition": None,
        "description": "The mixture curdles into inert, foul-smelling gray sludge.",
    },
]


def calculate_volatile_risk(reagents: list[str], catalyst: str | None = None) -> float:
    """Calculate the volatility risk score (0.0 to 1.0) for a combination of reagents."""
    if not reagents:
        return 0.0

    instabilities = []
    affinities = []
    for r in reagents:
        spec = REAGENTS_CATALOGUE.get(
            r, {"instability": 0.25, "affinity": "mineral", "secondary_affinity": "none"}
        )
        instabilities.append(spec["instability"])
        affinities.append(spec["affinity"])
        if spec.get("secondary_affinity") and spec["secondary_affinity"] != "none":
            affinities.append(spec["secondary_affinity"])

    base_risk = sum(instabilities) / len(instabilities)

    # Incompatible volatile affinities increase risk
    if "volatile" in affinities and "toxic" in affinities:
        base_risk += 0.30
    if affinities.count("volatile") >= 2:
        base_risk += 0.25
    if "radiant" in affinities and "toxic" in affinities:
        base_risk += 0.20

    # Synergistic pairs decrease risk
    if "radiant" in affinities and "botanical" in affinities:
        base_risk -= 0.15
    if "volatile" in affinities and "mineral" in affinities:
        base_risk -= 0.10

    # Apply catalyst modifier
    if catalyst and catalyst in CATALYSTS_CATALOGUE:
        base_risk += CATALYSTS_CATALOGUE[catalyst]["stability_bonus"]

    return max(0.05, min(0.95, round(base_risk, 2)))


class CraftingState(BaseModel):
    """Event-sourced state for crafting history, discovered recipes, and mishaps."""

    character_id: UUID | None = None
    total_crafts: int = 0
    successful_crafts: int = 0
    mishaps_count: int = 0
    discovered_recipes: list[str] = Field(default_factory=list)
    crafting_log: list[dict[str, Any]] = Field(default_factory=list)


class CraftingAggregate(DeclarativeAggregate[CraftingState]):
    """Event-sourced aggregate managing alchemical experimentation, recipes, and volatile risk."""

    aggregate_type = "Crafting"
    requires_creation_event = False

    def __init__(self, aggregate_id: Any = None, **kwargs: Any) -> None:
        super().__init__(aggregate_id=aggregate_id, **kwargs)
        if self._state is None:
            self._state = CraftingState(character_id=aggregate_id)

    @handles(CraftingAttempted)
    def handle_attempted(self, event: CraftingAttempted) -> None:
        if self._state is None:
            self._state = CraftingState(character_id=event.character_id)
        self.state.character_id = event.character_id
        self.state.total_crafts += 1
        self.state.crafting_log.append(
            {
                "event": "attempted",
                "reagents": event.reagents,
                "catalyst": event.catalyst,
                "risk_score": event.risk_score,
            }
        )

    @handles(CraftingSucceeded)
    def handle_succeeded(self, event: CraftingSucceeded) -> None:
        self.state.successful_crafts += 1
        if event.recipe_name not in self.state.discovered_recipes:
            self.state.discovered_recipes.append(event.recipe_name)
        self.state.crafting_log.append(
            {
                "event": "succeeded",
                "item_name": event.item_name,
                "quantity": event.quantity,
                "tags": event.tags,
            }
        )

    @handles(CraftingMishapOccurred)
    def handle_mishap(self, event: CraftingMishapOccurred) -> None:
        self.state.mishaps_count += 1
        self.state.crafting_log.append(
            {
                "event": "mishap",
                "mishap_type": event.mishap_type,
                "severity": event.severity,
                "damage_dealt": event.damage_dealt,
                "condition": event.condition_inflicted,
            }
        )

    def combine_reagents(
        self,
        character_id: UUID,
        reagents: list[str],
        catalyst: str | None = None,
        campaign_id: UUID | str = "",
        session_id: UUID | str = "",
        player_id: str | None = None,
        force_mishap: bool = False,
        risk_threshold: float = 0.50,
    ) -> dict[str, Any]:
        """Combine reagents in crucible, evaluate volatile outcome, and record domain events."""
        camp_uuid = None
        if campaign_id:
            try:
                camp_uuid = UUID(str(campaign_id))
            except Exception:
                camp_uuid = None

        sess_uuid = None
        if session_id:
            try:
                sess_uuid = UUID(str(session_id))
            except Exception:
                sess_uuid = None

        risk_score = calculate_volatile_risk(reagents, catalyst)
        self.create_event(
            CraftingAttempted,
            character_id=character_id,
            player_id=player_id,
            campaign_id=camp_uuid,
            session_id=sess_uuid,
            reagents=reagents,
            catalyst=catalyst,
            risk_score=risk_score,
        )

        is_mishap = force_mishap or (risk_score > risk_threshold and not catalyst)

        if is_mishap:
            # Select mishap based on risk
            mishap_entry = MISHAP_TABLE[0] if risk_score > 0.6 else MISHAP_TABLE[1]
            self.create_event(
                CraftingMishapOccurred,
                character_id=character_id,
                campaign_id=camp_uuid,
                session_id=sess_uuid,
                mishap_type=mishap_entry["mishap_type"],
                severity=mishap_entry["severity"],
                description=mishap_entry["description"],
                damage_dealt=mishap_entry["damage"],
                condition_inflicted=mishap_entry["condition"],
                reagents_lost=list(reagents),
            )
            return {
                "outcome": "mishap",
                "mishap": mishap_entry,
                "risk_score": risk_score,
                "reagents_lost": reagents,
            }

        # Successful crafting: search known recipes or generate experimental concoction
        reagent_set = set(reagents)
        matched = next((r for r in KNOWN_RECIPES if r["ingredients"] == reagent_set), None)

        if matched:
            item_name = matched["name"]
            recipe_name = matched["name"]
            tags = matched["tags"]
            properties = matched["properties"]
        else:
            item_name = f"Experimental Brew ({' & '.join(reagents)})"
            recipe_name = "Experimental Alchemy"
            tags = ["consumable", "experimental", "alchemy"]
            properties = {"potency": 2, "description": "A novel alchemical concoction."}

        self.create_event(
            CraftingSucceeded,
            character_id=character_id,
            campaign_id=camp_uuid,
            session_id=sess_uuid,
            recipe_name=recipe_name,
            item_name=item_name,
            quantity=1,
            tags=tags,
            reagents_consumed=list(reagents),
            catalyst_consumed=catalyst,
            properties=properties,
        )

        return {
            "outcome": "success",
            "item_name": item_name,
            "recipe_name": recipe_name,
            "quantity": 1,
            "tags": tags,
            "properties": properties,
            "risk_score": risk_score,
            "reagents_consumed": reagents,
            "catalyst_consumed": catalyst,
        }


__all__ = [
    "CATALYSTS_CATALOGUE",
    "KNOWN_RECIPES",
    "MISHAP_TABLE",
    "REAGENTS_CATALOGUE",
    "CraftingAggregate",
    "CraftingState",
    "calculate_volatile_risk",
]
