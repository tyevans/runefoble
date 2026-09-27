"""Dice, combat encounters, tactical previews, and reaction domain events."""

from __future__ import annotations

from typing import Any, ClassVar
from uuid import UUID, uuid4

from pydantic import Field

from runefoble_events.base import BaseRunefobleEvent, register_event
from runefoble_events.board_traps import TrapSprungEvent
from runefoble_events.combat_reactions import (
    CombatTurnPausedForReactionEvent,
    ReactionResolvedEvent,
)
from runefoble_events.vocal_dsp import VocalModulatorPresetAppliedEvent


@register_event("runefoble.events.dice.rolled")
class DiceRolled(BaseRunefobleEvent):
    suppress_event_type_warning: ClassVar[bool] = True
    aggregate_type: str = "GameSession"
    aggregate_id: UUID = Field(default_factory=uuid4)
    event_type: str = "runefoble.events.dice.rolled"
    session_id: str
    roller_id: str
    roller_name: str
    formula: str
    total: int
    rolls: list[int] = Field(default_factory=list)
    is_crit: bool = False
    is_fumble: bool = False

    @property
    def dice_notation(self) -> str:
        return self.formula

    @property
    def individual_rolls(self) -> list[int]:
        return self.rolls


DiceRollEvent = DiceRolled


@register_event("runefoble.events.encounter.spawned")
class EncounterSpawned(BaseRunefobleEvent):
    suppress_event_type_warning: ClassVar[bool] = True
    aggregate_type: str = "Encounter"
    aggregate_id: UUID = Field(default_factory=uuid4)
    event_type: str = "runefoble.events.encounter.spawned"
    session_id: str
    encounter_id: str
    encounter_name: str
    threat_level: str
    monsters: list[dict[str, Any]] = Field(default_factory=list)
    tactical_objective: str


@register_event("runefoble.events.encounter.action_resolved")
class AutonomousActionResolved(BaseRunefobleEvent):
    suppress_event_type_warning: ClassVar[bool] = True
    aggregate_type: str = "Encounter"
    aggregate_id: UUID = Field(default_factory=uuid4)
    event_type: str = "runefoble.events.encounter.action_resolved"
    session_id: str
    actor_name: str
    action_type: str
    target_name: str
    narrative: str
    hp_impact: int = 0


@register_event("runefoble.events.board.ghost_preview_candidate")
class CandidateGhostPreviewEmitted(BaseRunefobleEvent):
    suppress_event_type_warning: ClassVar[bool] = True
    aggregate_type: str = "BoardState"
    aggregate_id: UUID = Field(default_factory=uuid4)
    event_type: str = "runefoble.events.board.ghost_preview_candidate"
    session_id: str
    disambiguation_id: str
    candidate_id: str
    token_id: str
    target_x: int
    target_y: int
    descriptor: str
    path: list[list[int]] = Field(default_factory=list)


@register_event("runefoble.events.combat.reaction_prompt_triggered")
class ReactionPromptTriggered(CombatTurnPausedForReactionEvent):
    """Event emitted when a combat reaction prompt is triggered."""

    event_type: str = "runefoble.events.combat.reaction_prompt_triggered"


@register_event("runefoble.events.combat.reaction_opportunity_resolved")
class ReactionOpportunityResolved(ReactionResolvedEvent):
    """Event emitted when a combat reaction opportunity is resolved."""

    event_type: str = "runefoble.events.combat.reaction_opportunity_resolved"


@register_event("runefoble.events.board.secret_trap_triggered")
class SecretTrapTriggered(TrapSprungEvent):
    """Event emitted when a secret trap trigger is breached."""

    event_type: str = "runefoble.events.board.secret_trap_triggered"


@register_event("runefoble.events.voice.modulator_preset_changed")
class VocalModulatorPresetChanged(VocalModulatorPresetAppliedEvent):
    """Event emitted when a vocal modulation preset changes."""

    event_type: str = "runefoble.events.voice.modulator_preset_changed"


__all__ = [
    "AutonomousActionResolved",
    "CandidateGhostPreviewEmitted",
    "DiceRollEvent",
    "DiceRolled",
    "EncounterSpawned",
    "ReactionOpportunityResolved",
    "ReactionPromptTriggered",
    "SecretTrapTriggered",
    "VocalModulatorPresetChanged",
]
