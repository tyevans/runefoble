"""Domain events for TTRPG Rules Compendium and Encounter Builder."""

from typing import Any
from uuid import UUID

from pydantic import Field

from runefoble_events.base import BaseRunefobleEvent, register_event


@register_event("runefoble.events.compendium.homebrew_rule_registered")
class HomebrewRuleRegistered(BaseRunefobleEvent):
    """Emitted when a DM or player registers a campaign homebrew rule or monster."""

    event_type: str = "runefoble.events.compendium.homebrew_rule_registered"

    rule_id: UUID = Field(description="Unique homebrew rule aggregate identifier")
    campaign_id: UUID = Field(description="Campaign to which the homebrew rule belongs")
    author_id: str = Field(description="User ID of author or DM")
    rule_type: str = Field(description="Type of rule (monster, spell, condition, mechanic)")
    title: str = Field(description="Title of the homebrew entry")
    content: dict[str, Any] = Field(description="Structured rule or monster stat block")
    metadata: dict[str, Any] = Field(
        default_factory=dict, description="Additional homebrew metadata"
    )


@register_event("runefoble.events.compendium.encounter_balanced")
class EncounterBalanced(BaseRunefobleEvent):
    """Emitted when an encounter balancing calculation is performed and recorded."""

    event_type: str = "runefoble.events.compendium.encounter_balanced"

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
