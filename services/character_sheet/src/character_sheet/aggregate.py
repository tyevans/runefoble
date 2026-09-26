"""Event-sourced CharacterSheet aggregate using eventsource-py."""

from typing import Literal
from uuid import UUID

from eventsource.domain.aggregate import DeclarativeAggregate
from eventsource.domain.decorators import handles
from pydantic import BaseModel, Field
from runefoble_events.events import (
    AbsencePenaltyApplied,
    AbsencePenaltyCleared,
    CharacterCreated,
    CharacterHealthChanged,
)


class CharacterState(BaseModel):
    character_id: UUID
    name: str
    character_class: str
    max_hp: int
    current_hp: int
    player_id: str | None = None
    personality_traits: list[str] = Field(default_factory=list)
    penalties: dict[str, str] = Field(default_factory=dict)


class CharacterAggregate(DeclarativeAggregate[CharacterState]):
    """Event-sourced aggregate managing character stats, hit points, and session miss penalties."""

    aggregate_type = "CharacterSheet"
    requires_creation_event = True

    def create(
        self,
        name: str,
        character_class: str,
        max_hp: int = 30,
        player_id: str | None = None,
        personality_traits: list[str] | None = None,
    ) -> None:
        """Create a new character."""
        self.create_event(
            CharacterCreated,
            session_id=None,
            name=name,
            character_class=character_class,
            max_hp=max_hp,
            current_hp=max_hp,
            player_id=player_id,
            personality_traits=personality_traits or ["brave", "curious"],
        )

    def modify_health(self, delta: int, source: str = "damage") -> None:
        """Apply damage or healing."""
        new_hp = max(0, min(self.state.max_hp, self.state.current_hp + delta))
        self.create_event(
            CharacterHealthChanged,
            delta=delta,
            current_hp=new_hp,
            max_hp=self.state.max_hp,
            source=source,
        )

    def apply_penalty(
        self,
        penalty_type: Literal["drunk", "foolishness", "cowardice", "greed", "curse"],
        description: str,
        imposed_by: Literal["human_dm", "the_watcher"] = "the_watcher",
    ) -> None:
        """Apply a session miss penalty to an absent player's character."""
        self.create_event(
            AbsencePenaltyApplied,
            penalty_type=penalty_type,
            description=description,
            imposed_by=imposed_by,
        )

    def clear_penalty(self, penalty_type: str) -> None:
        """Clear an active penalty once the player returns or redeems themselves."""
        if penalty_type.lower() not in self.state.penalties:
            raise ValueError(f"Penalty '{penalty_type}' is not active on this character")
        self.create_event(
            AbsencePenaltyCleared,
            penalty_type=penalty_type.lower(),
        )

    # -----------------------------------------------------------------------
    # Event Handlers (@handles)
    # -----------------------------------------------------------------------

    @handles(CharacterCreated)
    def _on_created(self, event: CharacterCreated) -> None:
        self._state = CharacterState(
            character_id=event.aggregate_id,
            name=event.name,
            character_class=event.character_class,
            max_hp=event.max_hp,
            current_hp=event.current_hp,
            player_id=event.player_id,
            personality_traits=event.personality_traits,
        )

    @handles(CharacterHealthChanged)
    def _on_health_changed(self, event: CharacterHealthChanged) -> None:
        self._state = self.state.model_copy(update={"current_hp": event.current_hp})

    @handles(AbsencePenaltyApplied)
    def _on_penalty_applied(self, event: AbsencePenaltyApplied) -> None:
        pens = dict(self.state.penalties)
        pens[event.penalty_type.lower()] = event.description
        self._state = self.state.model_copy(update={"penalties": pens})

    @handles(AbsencePenaltyCleared)
    def _on_penalty_cleared(self, event: AbsencePenaltyCleared) -> None:
        pens = dict(self.state.penalties)
        pens.pop(event.penalty_type.lower(), None)
        self._state = self.state.model_copy(update={"penalties": pens})
