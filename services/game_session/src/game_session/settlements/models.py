"""Domain and API models for Cross-Campaign Settlements and Havens."""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field

FACILITY_TIER_NAMES: dict[str, dict[int, str]] = {
    "workshop": {1: "Field Forge", 2: "Master Guildhall", 3: "Arcane Crucible"},
    "sanctum": {1: "Resting Shrine", 2: "Hallowed Chapel", 3: "Ascendant Grove"},
    "fortifications": {1: "Wooden Palisades", 2: "Stone Ramparts", 3: "Adamantine Citadel"},
    "watchtower": {1: "Scout Perch", 2: "Signal Spire", 3: "Celestial Beacon"},
    "trading_post": {1: "Caravan Depot", 2: "Merchant Bazaar", 3: "Grand Exchange"},
}

FACILITY_REST_BOONS: dict[str, str] = {
    "sanctum": "Sanctuary Rest: Advantage on death saves and bonus hit dice on campfire rest.",
    "workshop": "Mastercraft: Reagent crafting costs reduced by 25% for visiting parties.",
    "fortifications": "Bastion Guard: +2 AC defense against frontier wilderness ambushes.",
    "watchtower": "Vigilant Eyes: Early detection of wandering hostile factions within 10 miles.",
    "trading_post": "Frontier Trade: Unlocks rare regional alchemical reagents and export goods.",
}

DEFAULT_FACILITIES: dict[str, int] = {
    "workshop": 1,
    "sanctum": 1,
    "fortifications": 1,
    "watchtower": 1,
}


class SettlementState(BaseModel):
    """Event-sourced state of a shared West Marches frontier settlement or haven."""

    settlement_id: str = ""
    shared_world_id: str = ""
    name: str = "Frontier Haven"
    settlement_type: str = "outpost"  # outpost, haven, fortress, sanctuary
    region: str = "Wilderness"
    coordinates: dict[str, float] = Field(default_factory=dict)
    founded_by_campaign_id: str = ""
    chartered_by: str = ""
    level: int = 1
    defense_rating: int = 10
    facilities: dict[str, int] = Field(
        default_factory=lambda: {
            "workshop": 1,
            "sanctum": 1,
            "fortifications": 1,
            "watchtower": 1,
        }
    )
    contributing_campaigns: list[str] = Field(default_factory=list)
    active_boons: dict[str, str] = Field(default_factory=dict)
    materials_treasury: dict[str, int] = Field(default_factory=dict)
    gold_invested: int = 0


class CharterSettlementRequest(BaseModel):
    """Request payload to charter a new communal haven or outpost."""

    name: str
    shared_world_id: str
    settlement_type: str = "outpost"
    region: str = "Wilderness"
    coordinates: dict[str, float] = Field(default_factory=dict)
    founded_by_campaign_id: str = ""
    facilities: dict[str, int] | None = None
    defense_rating: int = 10
    metadata: dict[str, Any] = Field(default_factory=dict)


class UpgradeFacilityRequest(BaseModel):
    """Request payload to upgrade a settlement facility or fortification tier."""

    facility_id: str
    contributing_campaign_id: str = ""
    gold_spent: int = 0
    materials_spent: dict[str, int] = Field(default_factory=dict)


class ClaimRestBoonRequest(BaseModel):
    """Request payload to claim a sanctum rest boon for a character or party."""

    campaign_id: str
    character_id: str = ""
    facility_id: str = "sanctum"
