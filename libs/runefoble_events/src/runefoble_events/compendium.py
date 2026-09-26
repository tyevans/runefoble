"""Domain events for TTRPG Rules Compendium and Encounter Builder."""

from typing import Any
from uuid import UUID

from pydantic import Field

from runefoble_events.base import BaseRunefobleEvent, register_event


@register_event
class MonsterIndexed(BaseRunefobleEvent):
    """Emitted when a monster stat block is indexed into the rules compendium."""

    event_type: str = "MonsterIndexed"
    monster_id: UUID = Field(description="Unique monster identifier")
    name: str = Field(description="Monster name (e.g., Goblin, Bugbear, Ogre)")
    challenge_rating: float = Field(description="Challenge rating (CR)")
    creature_type: str = Field(description="Creature type (e.g., humanoid, fiend, dragon)")
    size: str = Field(
        default="Medium", description="Size category (Small, Medium, Large, Huge, Gargantuan)"
    )
    armor_class: int = Field(description="Armor Class (AC)")
    hit_points: int = Field(description="Hit Points (HP)")
    xp: int = Field(description="Experience points awarded for defeating monster")
    role: str = Field(
        default="brute",
        description="Combat role (brute, artillery, controller, skirmisher, leader)",
    )
    metadata: dict[str, Any] = Field(
        default_factory=dict, description="Additional monster attributes and actions"
    )


@register_event
class SpellIndexed(BaseRunefobleEvent):
    """Emitted when a spell definition is indexed into the rules compendium."""

    event_type: str = "SpellIndexed"
    spell_id: UUID = Field(description="Unique spell identifier")
    name: str = Field(description="Spell name (e.g., Fireball, Cure Wounds)")
    level: int = Field(description="Spell level (0 for cantrips)")
    school: str = Field(description="Magic school (Evocation, Abjuration, etc.)")
    casting_time: str = Field(description="Casting time (e.g., 1 action, 1 bonus action)")
    range: str = Field(description="Spell range (e.g., 60 feet, Self)")
    components: str = Field(description="Spell components (V, S, M)")
    duration: str = Field(
        description="Spell duration (e.g., Instantaneous, Concentration 1 minute)"
    )
    description: str = Field(description="Spell mechanical text and effects")
    metadata: dict[str, Any] = Field(default_factory=dict, description="Additional spell metadata")


@register_event
class ConditionIndexed(BaseRunefobleEvent):
    """Emitted when a condition rule is indexed into the rules compendium."""

    event_type: str = "ConditionIndexed"
    condition_id: UUID = Field(description="Unique condition identifier")
    name: str = Field(description="Condition name (e.g., Blinded, Prone, Stunned)")
    description: str = Field(description="Condition rules and gameplay effects")
    effects: list[str] = Field(default_factory=list, description="Bullet point gameplay mechanics")
    metadata: dict[str, Any] = Field(
        default_factory=dict, description="Additional condition metadata"
    )


@register_event
class HomebrewRuleRegistered(BaseRunefobleEvent):
    """Emitted when a DM or player registers a campaign homebrew rule or monster."""

    event_type: str = "HomebrewRuleRegistered"
    rule_id: UUID = Field(description="Unique homebrew rule aggregate identifier")
    campaign_id: UUID = Field(description="Campaign to which the homebrew rule belongs")
    author_id: str = Field(description="User ID of author or DM")
    rule_type: str = Field(description="Type of rule (monster, spell, condition, mechanic)")
    title: str = Field(description="Title of the homebrew entry")
    content: dict[str, Any] = Field(description="Structured rule or monster stat block")
    metadata: dict[str, Any] = Field(
        default_factory=dict, description="Additional homebrew metadata"
    )


@register_event
class EncounterBalanced(BaseRunefobleEvent):
    """Emitted when an encounter balancing calculation is performed and recorded."""

    event_type: str = "EncounterBalanced"
    encounter_id: UUID = Field(description="Unique encounter computation identifier")
    campaign_id: UUID | None = Field(default=None, description="Optional campaign context")
    party_levels: list[int] = Field(description="List of character levels in the party")
    target_difficulty: str = Field(description="Target difficulty (Easy, Medium, Hard, Deadly)")
    total_party_xp_threshold: dict[str, int] = Field(
        description="Party XP thresholds per difficulty tier"
    )
    selected_monsters: list[dict[str, Any]] = Field(
        description="Selected monsters in the encounter group"
    )
    total_xp: int = Field(description="Raw sum of monster XP")
    adjusted_xp: int = Field(description="Adjusted encounter XP accounting for action economy")
    difficulty_tier: str = Field(description="Calculated encounter difficulty tier")
    multiplier: float = Field(description="Action economy multiplier applied")
