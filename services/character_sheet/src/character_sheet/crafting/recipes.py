"""Alchemical recipe catalogue, reagent affinities, and ingredient schemas."""

from __future__ import annotations

from typing import Any
from uuid import UUID

from pydantic import BaseModel, Field

_RAW_REAGENTS = [
    ("Glowmoss Extract", "radiant", "botanical", 0.10, 2, "Illuminating azure fluid."),
    ("Volcano Ash", "volatile", "mineral", 0.35, 3, "Sulfuric volcanic powder."),
    ("Star Lily", "radiant", "botanical", 0.05, 2, "Blooms under starlight."),
    ("Wyrm Blood", "draconic", "volatile", 0.40, 4, "Radiating dragon blood."),
    ("Nightshade Berry", "toxic", "botanical", 0.30, 2, "Paralyzing alkaloids."),
    ("Purified Quicksilver", "arcane", "mineral", 0.20, 3, "Liquid silver conduit."),
    ("Frost Lichen", "aqueous", "botanical", 0.15, 2, "Glacial tundra lichen."),
]

REAGENTS_CATALOGUE: dict[str, dict[str, Any]] = {
    name: {"affinity": a, "secondary_affinity": s, "instability": i, "potency": p, "description": d}
    for name, a, s, i, p, d in _RAW_REAGENTS
}

_RAW_CATALYSTS = [
    ("purified_water", -0.20, 0, "Neutral distilled spring water."),
    ("dragon_bile", 0.15, 2, "Hyper-reactive enzymatic fluid."),
    ("quicksilver", -0.15, 1, "Fluid metal catalyst."),
    ("spirit_ash", -0.25, 0, "Blessed ceremonial ash."),
]

CATALYSTS_CATALOGUE: dict[str, dict[str, Any]] = {
    name: {"stability_bonus": sb, "potency_mod": pm, "description": desc}
    for name, sb, pm, desc in _RAW_CATALYSTS
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


class Recipe(BaseModel):
    """Schema representing an alchemical recipe specification."""

    name: str
    ingredients: set[str] | list[str]
    tags: list[str] = Field(default_factory=list)
    description: str = ""
    properties: dict[str, Any] = Field(default_factory=dict)
    dc: int = 10


class CraftingState(BaseModel):
    """Event-sourced state for crafting history, discovered recipes, and mishaps."""

    character_id: UUID | None = None
    total_crafts: int = 0
    successful_crafts: int = 0
    mishaps_count: int = 0
    discovered_recipes: list[str] = Field(default_factory=list)
    crafting_log: list[dict[str, Any]] = Field(default_factory=list)

    def record(self, kind: str, **kw: Any) -> None:
        self.crafting_log.append({"event": kind, **kw})


def calculate_crafting_dc(reagents: list[str] | set[str], base_dc: int = 10) -> int:
    """Calculate difficulty check for an alchemical synthesis attempt."""
    return base_dc + sum(REAGENTS_CATALOGUE.get(r, {}).get("potency", 1) for r in reagents)


def find_matching_recipe(reagents: list[str] | set[str]) -> dict[str, Any] | None:
    """Find a canonical recipe matching the exact set of crucible reagents."""
    reagent_set = set(reagents)
    return next((r for r in KNOWN_RECIPES if set(r["ingredients"]) == reagent_set), None)
