"""Event models for Runefoble reactive gameplay, powered by eventsource-py.

All domain events subclass eventsource.domain.event.DomainEvent and are registered
in the global EventRegistry for serialization, stream persistence, and replay.
"""

from typing import Any, Literal
from uuid import UUID, uuid4

from eventsource.domain.event import DomainEvent
from eventsource.domain.event_registry import register_event
from pydantic import Field

# ---------------------------------------------------------------------------
# Base Runefoble Domain Event
# ---------------------------------------------------------------------------


class BaseRunefobleEvent(DomainEvent):
    """Base domain event for Runefoble, inheriting from eventsource-py DomainEvent.

    Provides CloudEvent compatibility while supporting full EventStore persistence,
    versioning, causation/correlation tracking, and multi-tenant scoping.
    """

    campaign_id: UUID | None = Field(default=None, description="Campaign identifier")
    session_id: UUID | None = Field(default=None, description="Game session identifier")

    def to_cloudevent_dict(self) -> dict[str, Any]:
        """Convert domain event to standard CloudEvents 1.0 JSON format."""
        return {
            "specversion": "1.0",
            "id": str(self.event_id),
            "source": f"/runefoble/{self.aggregate_type.lower()}/{self.aggregate_id}",
            "type": f"runefoble.{self.event_type.lower()}",
            "time": self.occurred_at.isoformat(),
            "datacontenttype": "application/json",
            "data": self.model_dump(mode="json"),
        }


# ---------------------------------------------------------------------------
# GameSession Aggregate Events
# ---------------------------------------------------------------------------


@register_event
class SessionCreated(BaseRunefobleEvent):
    aggregate_type: str = "GameSession"
    title: str = "Untitled Session"
    dm_id: str = "the_watcher"
    created_by: str = "system"


@register_event
class SessionStarted(BaseRunefobleEvent):
    aggregate_type: str = "GameSession"
    started_at_turn: int = 1


@register_event
class PlayerJoinedSession(BaseRunefobleEvent):
    aggregate_type: str = "GameSession"
    player_id: str
    character_id: UUID
    character_name: str
    character_class: str


@register_event
class PlayerLeftSession(BaseRunefobleEvent):
    aggregate_type: str = "GameSession"
    player_id: str
    reason: str = "disconnected"


@register_event
class TurnAdvanced(BaseRunefobleEvent):
    aggregate_type: str = "GameSession"
    previous_turn: int
    new_turn: int
    active_character_id: UUID | None = None


@register_event
class SessionEnded(BaseRunefobleEvent):
    aggregate_type: str = "GameSession"
    summary: str = "Session completed"


# ---------------------------------------------------------------------------
# BoardState Aggregate Events
# ---------------------------------------------------------------------------


@register_event
class BoardGridInitialized(BaseRunefobleEvent):
    aggregate_type: str = "BoardState"
    width: int = 20
    height: int = 20
    cell_size_px: int = 40
    grid_type: Literal["square", "hex"] = "square"
    session_id_str: str = ""


@register_event
class TokenPlaced(BaseRunefobleEvent):
    aggregate_type: str = "BoardState"
    token_id: str = Field(default_factory=lambda: str(uuid4()))
    name: str
    token_type: Literal["pc", "monster", "npc", "obstacle"]
    x: int
    y: int
    hp: int | None = None
    is_friendly: bool = False


@register_event
class TokenMoved(BaseRunefobleEvent):
    aggregate_type: str = "BoardState"
    token_id: str
    name: str
    from_x: int
    from_y: int
    to_x: int
    to_y: int
    initiated_by: Literal["player", "the_watcher", "stand_in"] = "player"


@register_event
class TokenRemoved(BaseRunefobleEvent):
    aggregate_type: str = "BoardState"
    token_id: str
    reason: str = "defeated"


@register_event
class FogOfWarRevealed(BaseRunefobleEvent):
    aggregate_type: str = "BoardState"
    revealed_cells: list[list[int]] = Field(default_factory=list)
    revealed_by_token_id: str | None = None


# ---------------------------------------------------------------------------
# CharacterSheet Aggregate Events
# ---------------------------------------------------------------------------


@register_event
class CharacterCreated(BaseRunefobleEvent):
    aggregate_type: str = "CharacterSheet"
    name: str
    character_class: str
    max_hp: int
    current_hp: int
    player_id: str | None = None
    personality_traits: list[str] = Field(default_factory=list)


@register_event
class CharacterHealthChanged(BaseRunefobleEvent):
    aggregate_type: str = "CharacterSheet"
    delta: int
    current_hp: int
    max_hp: int
    source: str = "damage"


@register_event
class AbsencePenaltyApplied(BaseRunefobleEvent):
    aggregate_type: str = "CharacterSheet"
    penalty_type: Literal["drunk", "foolishness", "cowardice", "greed", "curse"]
    description: str
    imposed_by: Literal["human_dm", "the_watcher"] = "the_watcher"


@register_event
class AbsencePenaltyCleared(BaseRunefobleEvent):
    aggregate_type: str = "CharacterSheet"
    penalty_type: str


@register_event
class ItemAddedToInventory(BaseRunefobleEvent):
    aggregate_type: str = "CharacterSheet"
    item_id: str
    name: str
    quantity: int = 1
    weight_lbs: float = 0.0


@register_event
class ItemRemovedFromInventory(BaseRunefobleEvent):
    aggregate_type: str = "CharacterSheet"
    item_id: str
    quantity: int = 1


@register_event
class EquipmentSlotUpdated(BaseRunefobleEvent):
    aggregate_type: str = "CharacterSheet"
    slot: str
    item_name: str | None = None


@register_event
class ConditionApplied(BaseRunefobleEvent):
    aggregate_type: str = "CharacterSheet"
    condition: str
    duration_rounds: int | None = None
    source: str = ""


@register_event
class ConditionRemoved(BaseRunefobleEvent):
    aggregate_type: str = "CharacterSheet"
    condition: str


# ---------------------------------------------------------------------------
# The Watcher, Voice, and Gameplay Stream Events
# ---------------------------------------------------------------------------


@register_event
class PlayerSpokeEvent(BaseRunefobleEvent):
    aggregate_type: str = "GameSession"
    speaker_id: str
    speaker_name: str
    transcript: str
    is_whisper: bool = False
    target_character_id: str | None = None


@register_event
class SpeechIntentParsed(BaseRunefobleEvent):
    aggregate_type: str = "GameSession"
    speaker_name: str
    action_type: str
    target: str | None = None
    confidence: float = 1.0
    flavor_text: str = ""
    raw_transcript: str = ""


@register_event
class WatcherNarrationGenerated(BaseRunefobleEvent):
    aggregate_type: str = "GameSession"
    narrative_text: str
    tone: str = "dark_fantasy"
    sensory_details: list[str] = Field(default_factory=list)
    suggested_prompts: list[str] = Field(default_factory=list)
    tension_level: str = "rising"


@register_event
class StandInActionDecided(BaseRunefobleEvent):
    aggregate_type: str = "GameSession"
    character_name: str
    action_type: str
    dialogue: str
    penalties_applied: list[str] = Field(default_factory=list)
    flavor_text: str = ""


@register_event
class DiceRolled(BaseRunefobleEvent):
    aggregate_type: str = "GameSession"
    roller_name: str
    dice_notation: str
    individual_rolls: list[int]
    modifier: int = 0
    total: int
    reason: str = "Skill check"


# Backward-compatible aliases for legacy imports
WatcherNarrationEvent = WatcherNarrationGenerated
BoardMoveEvent = TokenMoved
DiceRollEvent = DiceRolled
SessionPenaltyEvent = AbsencePenaltyApplied
