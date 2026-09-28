"""Domain models, schemas, and enums for settlement haven builder and establishments.

Governed by ADR-0002, ADR-0007, and PRD-0024.
"""

from __future__ import annotations

from enum import StrEnum
from typing import Any

from pydantic import BaseModel, Field


class SettlementScale(StrEnum):
    """Civic scale of a persistent frontier settlement or haven."""

    HAMLET = "hamlet"
    VILLAGE = "village"
    MARKET_TOWN = "market_town"
    CITY = "city"
    METROPOLIS = "metropolis"


class EstablishmentCategory(StrEnum):
    """Functional category of an establishment in a settlement district."""

    HOSPITALITY = "hospitality"
    COMMERCE = "commerce"
    CIVIC = "civic"
    FAITH = "faith"
    UNDERWORLD = "underworld"


class BulletinBoardType(StrEnum):
    """Physical location and atmosphere of a community notice board."""

    TOWN_SQUARE = "town_square"
    TAVERN = "tavern"
    GUILDHALL = "guildhall"


class BulletinCategory(StrEnum):
    """Functional category of a pinned proclamation or parchment note."""

    BOUNTY = "bounty"
    RUMOR = "rumor"
    ORDINANCE = "ordinance"
    JOB = "job"


SCALE_TO_TIER: dict[str, int] = {
    "hamlet": 1,
    "thorp": 1,
    "village": 2,
    "frontier_haven": 2,
    "market_town": 3,
    "city": 4,
    "fortified_city": 4,
    "metropolis": 5,
}

TIER_TO_SCALE: dict[int, str] = {
    1: "hamlet",
    2: "village",
    3: "market_town",
    4: "city",
    5: "metropolis",
}

SCALE_MAX_DISTRICTS: dict[int, int] = {
    1: 2,
    2: 4,
    3: 8,
    4: 16,
    5: 32,
}

TIER_MIN_PROSPERITY: dict[int, int] = {
    1: 0,
    2: 100,
    3: 300,
    4: 600,
    5: 1000,
}

DEFAULT_TIER_DISTRICTS: dict[int, list[str]] = {
    1: ["commons", "residential"],
    2: ["agricultural_commons", "defensive_palisade", "trading_post"],
    3: ["artisan_quarter", "town_watch_barracks", "market_plaza"],
    4: ["high_citadel", "temple_quarter", "docks", "entertainment_quarter"],
    5: ["imperial_banks", "planar_curio_market", "civic_coliseum"],
}

DEFAULT_FACILITIES: dict[str, int] = {
    "workshop": 1,
    "sanctum": 1,
    "fortifications": 1,
    "watchtower": 1,
}

FACILITY_REST_BOONS: dict[str, str] = {
    "sanctum": "Sanctuary Rest: Advantage on death saves and bonus hit dice on campfire rest.",
    "workshop": "Mastercraft: Reagent crafting costs reduced by 25% for visiting parties.",
    "fortifications": "Bastion Guard: +2 AC defense against frontier wilderness ambushes.",
    "watchtower": "Vigilant Eyes: Early detection of wandering hostile factions within 10 miles.",
    "trading_post": "Frontier Trade: Unlocks rare regional alchemical reagents and export goods.",
}

FACILITY_TIER_NAMES: dict[str, dict[int, str]] = {
    "workshop": {1: "Field Forge", 2: "Master Guildhall", 3: "Arcane Crucible"},
    "sanctum": {1: "Resting Shrine", 2: "Hallowed Chapel", 3: "Ascendant Grove"},
    "fortifications": {1: "Wooden Palisades", 2: "Stone Ramparts", 3: "Adamantine Citadel"},
    "watchtower": {1: "Scout Perch", 2: "Signal Spire", 3: "Celestial Beacon"},
    "trading_post": {1: "Caravan Depot", 2: "Merchant Bazaar", 3: "Grand Exchange"},
}


class BulletinNoticeState(BaseModel):
    """Event-sourced state of a notice pinned to a settlement bulletin board."""

    notice_id: str
    settlement_id: str
    board_type: str = "town_square"
    title: str
    author_id: str
    category: str = "rumor"
    content: str
    wax_sealed: bool = False
    cipher_encoded: bool = False
    cipher_puzzle: str = "rot13"
    cipher_solution: str = ""
    cipher_hint: str = ""
    hidden_content: str = ""
    decrypted_by: list[str] = Field(default_factory=list)
    status: str = "active"
    created_at: str = ""
    metadata: dict[str, Any] = Field(default_factory=dict)


class SettlementState(BaseModel):
    """Event-sourced state of a persistent settlement haven and district layout."""

    settlement_id: str = ""
    campaign_id: str = ""
    shared_world_id: str = ""
    name: str = "Frontier Haven"
    scale: str = "hamlet"
    tier: int = 1
    biome: str = "river_confluence"
    coordinates: dict[str, float] = Field(default_factory=dict)
    prosperity: int = 0
    max_districts: int = 2
    districts: list[str] = Field(default_factory=list)
    defense_rating: int = 10
    facilities: dict[str, int] = Field(default_factory=lambda: dict(DEFAULT_FACILITIES))
    contributing_campaigns: list[str] = Field(default_factory=list)
    active_boons: dict[str, str] = Field(default_factory=dict)
    materials_treasury: dict[str, int] = Field(default_factory=dict)
    gold_invested: int = 0
    level: int = 1
    settlement_type: str = "haven"
    region: str = "Wilderness"
    chartered_by: str = ""
    is_founded: bool = False
    bulletin_notices: dict[str, BulletinNoticeState] = Field(default_factory=dict)


class EstablishmentState(BaseModel):
    """Event-sourced state of a commercial, civic, or hospitality establishment."""

    establishment_id: str = ""
    settlement_id: str = ""
    district_id: str = ""
    category: str = "commerce"
    name: str = "Storefront"
    campaign_id: str = ""
    tier: int = 1
    capacity: int = 10
    operating_cost: int = 5
    amenities: list[str] = Field(default_factory=list)
    status: str = "operational"
    owner_id: str = ""
    is_constructed: bool = False
    staff: list[str] = Field(default_factory=list)
    staff_count: int = 0
    total_wages: int = 0
    net_operating_cost: int = 5
    projected_service_quality: float = 1.0
    service_quality_tier: str = "standard"
    interpersonal_tension_index: float = 0.0
    metadata: dict[str, Any] = Field(default_factory=dict)


class FoundSettlementRequest(BaseModel):
    """Request payload to found a new settlement haven."""

    name: str
    scale: str = "village"
    biome: str = "river_confluence"
    coordinates: dict[str, float] = Field(default_factory=dict)
    prosperity: int = 0
    districts: list[str] | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)


class ConstructEstablishmentRequest(BaseModel):
    """Request payload to construct an establishment in a settlement district."""

    district_id: str
    category: str
    name: str
    tier: int = 1
    capacity: int = 10
    operating_cost: int = 5
    amenities: list[str] = Field(default_factory=list)
    metadata: dict[str, Any] = Field(default_factory=dict)


class UpgradeSettlementTierRequest(BaseModel):
    """Request payload to upgrade settlement civic tier."""

    new_tier: int | None = None
    target_scale: str | None = None
    prosperity: int | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)


class UpgradeEstablishmentRequest(BaseModel):
    """Request payload to upgrade an establishment."""

    tier: int | None = None
    added_amenities: list[str] = Field(default_factory=list)
    capacity: int | None = None
    operating_cost: int | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)


class SettlementProjectionResponse(BaseModel):
    """Consolidated read projection for a settlement and its establishments."""

    settlement_id: str
    campaign_id: str
    shared_world_id: str = ""
    name: str
    scale: str
    tier: int
    biome: str
    coordinates: dict[str, float]
    prosperity: int
    max_districts: int
    districts: list[str]
    defense_rating: int = 10
    facilities: dict[str, int] = Field(default_factory=dict)
    active_boons: dict[str, str] = Field(default_factory=dict)
    establishments: list[EstablishmentState] = Field(default_factory=list)


class PinBulletinNoticeRequest(BaseModel):
    """Request payload to pin a notice or bounty to a settlement bulletin board."""

    board_type: str = "town_square"
    title: str
    category: str = "rumor"
    content: str
    wax_sealed: bool = False
    cipher_encoded: bool = False
    cipher_puzzle: str = "rot13"
    cipher_solution: str = ""
    cipher_hint: str = ""
    hidden_content: str = ""
    metadata: dict[str, Any] = Field(default_factory=dict)


class DecryptCipherNoticeRequest(BaseModel):
    """Request payload to submit a cipher decryption solution."""

    solution: str


class BulletinNoticeResponse(BaseModel):
    """Client projection of a pinned bulletin notice with selective cipher masking."""

    notice_id: str
    settlement_id: str
    board_type: str
    title: str
    author_id: str
    category: str
    content: str
    wax_sealed: bool = False
    cipher_encoded: bool = False
    cipher_puzzle: str = ""
    cipher_hint: str = ""
    hidden_content: str | None = None
    is_decrypted: bool = False
    status: str = "active"
    created_at: str = ""
    metadata: dict[str, Any] = Field(default_factory=dict)
