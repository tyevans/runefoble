"""Pydantic data models for the Rules Compendium and Encounter Builder."""

from typing import Any
from uuid import UUID

from pydantic import BaseModel, Field


class MonsterStatBlock(BaseModel):
    """Monster stat block model."""

    monster_id: UUID | None = None
    name: str
    challenge_rating: float
    creature_type: str
    size: str = "Medium"
    armor_class: int
    hit_points: int
    speed: str = "30 ft."
    xp: int
    role: str = "brute"
    stats: dict[str, int] = Field(default_factory=dict)
    actions: list[dict[str, Any]] = Field(default_factory=list)
    traits: list[dict[str, Any]] = Field(default_factory=list)
    description: str = ""
    is_homebrew: bool = False
    campaign_id: UUID | None = None


class SpellModel(BaseModel):
    """Spell definition model."""

    spell_id: UUID | None = None
    name: str
    level: int
    school: str
    casting_time: str
    range: str
    components: str
    duration: str
    description: str
    is_homebrew: bool = False
    campaign_id: UUID | None = None


class ConditionModel(BaseModel):
    """Condition mechanics model."""

    condition_id: UUID | None = None
    name: str
    description: str
    effects: list[str] = Field(default_factory=list)


class HomebrewCreateRequest(BaseModel):
    """Request payload to register a custom campaign homebrew rule or monster."""

    campaign_id: UUID
    rule_type: str = Field(description="'monster', 'spell', 'condition', or 'mechanic'")
    title: str
    content: dict[str, Any]


class HomebrewResponse(BaseModel):
    """Response payload for registered homebrew rule."""

    rule_id: UUID
    campaign_id: UUID
    author_id: str
    rule_type: str
    title: str
    content: dict[str, Any]
    status: str = "registered"


class EncounterBalanceRequest(BaseModel):
    """Request to balance an encounter for a given party roster."""

    party_levels: list[int] = Field(
        min_length=1,
        description="List of player character levels, e.g. [3, 3, 3, 4]",
    )
    target_difficulty: str = Field(
        default="Medium",
        description="Target difficulty: 'Easy', 'Medium', 'Hard', or 'Deadly'",
    )
    environment: str | None = Field(default=None, description="Optional environment context")
    desired_roles: list[str] | None = Field(
        default=None, description="Optional desired combat roles (e.g. ['brute', 'artillery'])"
    )
    campaign_id: UUID | None = None


class MonsterGroupRecommendation(BaseModel):
    """Recommended monster count and tactical role within an encounter."""

    name: str
    cr: float
    xp: int
    count: int
    role: str
    subtotal_xp: int


class EncounterBalanceResponse(BaseModel):
    """Result of automated CR encounter balancing calculation."""

    encounter_id: UUID
    party_levels: list[int]
    party_size: int
    target_difficulty: str
    difficulty_tier: str
    total_party_xp_threshold: dict[str, int]
    monsters: list[MonsterGroupRecommendation]
    total_monster_count: int
    total_raw_xp: int
    multiplier: float
    adjusted_xp: int
    tactical_summary: str


class RuleSearchResultItem(BaseModel):
    """Single matching rule result item."""

    category: str
    name: str
    score: float
    summary: str
    details: dict[str, Any]
    is_homebrew: bool = False
    campaign_id: UUID | None = None


class RuleSearchResponse(BaseModel):
    """Search response across rules compendium."""

    query: str
    results_count: int
    took_ms: float
    results: list[RuleSearchResultItem]
