"""Domain events for combat reaction interrupts and ready-action triggers."""

from __future__ import annotations

import time
from typing import Any, ClassVar
from uuid import UUID, uuid4

from pydantic import Field

from runefoble_events.base import BaseRunefobleEvent, register_event


@register_event("combat.turn.paused_for_reaction")
@register_event("runefoble.events.combat.turn_paused_for_reaction")
class CombatTurnPausedForReactionEvent(BaseRunefobleEvent):
    """Emitted when active combat turn is halted for a spoken reaction interrupt."""

    suppress_event_type_warning: ClassVar[bool] = True
    aggregate_type: str = "GameSession"
    aggregate_id: UUID = Field(default_factory=uuid4)
    event_type: str = "combat.turn.paused_for_reaction"
    session_id: UUID | str = ""
    reaction_id: str = Field(default_factory=lambda: str(uuid4()))
    reacting_combatant_id: str = ""
    reacting_combatant_name: str = ""
    trigger_phrase: str = ""
    reaction_type: str = "reaction"
    paused_turn_combatant_id: str = ""
    timeout_seconds: float = 15.0
    timestamp: float = Field(default_factory=time.time)
    details: dict[str, Any] = Field(default_factory=dict)


@register_event("combat.reaction.resolved")
@register_event("runefoble.events.combat.reaction_resolved")
class ReactionResolvedEvent(BaseRunefobleEvent):
    """Emitted when a declared combat reaction interrupt is resolved or dismissed."""

    suppress_event_type_warning: ClassVar[bool] = True
    aggregate_type: str = "GameSession"
    aggregate_id: UUID = Field(default_factory=uuid4)
    event_type: str = "combat.reaction.resolved"
    session_id: UUID | str = ""
    reaction_id: str = ""
    reacting_combatant_id: str = ""
    action_taken: str = "executed"
    resumed: bool = True
    details: dict[str, Any] = Field(default_factory=dict)


@register_event("combat.ready_action.registered")
@register_event("runefoble.events.combat.ready_action_registered")
class ReadyActionRegisteredEvent(BaseRunefobleEvent):
    """Emitted when a combatant registers a conditional ready-action trigger."""

    suppress_event_type_warning: ClassVar[bool] = True
    aggregate_type: str = "GameSession"
    aggregate_id: UUID = Field(default_factory=uuid4)
    event_type: str = "combat.ready_action.registered"
    session_id: UUID | str = ""
    ready_action_id: str = Field(default_factory=lambda: str(uuid4()))
    combatant_id: str = ""
    combatant_name: str = ""
    trigger_type: str = "spatial"
    trigger_condition: str = ""
    target_id: str | None = None
    range_cells: int | None = None
    readied_action: str = ""
    details: dict[str, Any] = Field(default_factory=dict)


@register_event("combat.ready_action.triggered")
@register_event("runefoble.events.combat.ready_action_triggered")
class ReadyActionTriggeredEvent(BaseRunefobleEvent):
    """Emitted when an incoming combat or board event fulfills a ready-action trigger."""

    suppress_event_type_warning: ClassVar[bool] = True
    aggregate_type: str = "GameSession"
    aggregate_id: UUID = Field(default_factory=uuid4)
    event_type: str = "combat.ready_action.triggered"
    session_id: UUID | str = ""
    ready_action_id: str = ""
    combatant_id: str = ""
    combatant_name: str = ""
    triggering_entity_id: str = ""
    trigger_type: str = ""
    readied_action: str = ""
    details: dict[str, Any] = Field(default_factory=dict)


CombatTurnPausedForReaction = CombatTurnPausedForReactionEvent
ReactionResolved = ReactionResolvedEvent
ReadyActionRegistered = ReadyActionRegisteredEvent
ReadyActionTriggered = ReadyActionTriggeredEvent
