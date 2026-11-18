"""Event-sourced Compendium and Encounter aggregates using eventsource-py."""

from typing import Any
from uuid import UUID

from eventsource.domain.aggregate import DeclarativeAggregate
from eventsource.domain.decorators import handles
from pydantic import BaseModel, Field
from runefoble_events.events import (
    EncounterBalanced,
    HomebrewRuleRegistered,
)


class CompendiumState(BaseModel):
    """Internal state representation for campaign homebrew rules, keyed by rule id."""

    compendium_id: UUID
    homebrew_rules: dict[str, dict[str, Any]] = Field(default_factory=dict)


class CompendiumAggregate(DeclarativeAggregate[CompendiumState]):
    """Event-sourced aggregate managing campaign homebrew rule registration."""

    aggregate_type = "Compendium"
    requires_creation_event = False

    def __init__(self, aggregate_id: UUID) -> None:
        super().__init__(aggregate_id)
        self._state = self._get_initial_state()

    def _get_initial_state(self) -> CompendiumState:
        return CompendiumState(compendium_id=self.aggregate_id)

    def register_homebrew(
        self,
        rule_id: UUID,
        campaign_id: UUID,
        author_id: str,
        rule_type: str,
        title: str,
        content: dict[str, Any],
        metadata: dict[str, Any] | None = None,
    ) -> None:
        """Register a campaign homebrew rule or custom monster."""
        self.create_event(
            HomebrewRuleRegistered,
            aggregate_id=self.aggregate_id,
            rule_id=rule_id,
            campaign_id=campaign_id,
            author_id=author_id,
            rule_type=rule_type,
            title=title,
            content=content,
            metadata=metadata or {},
        )

    # -----------------------------------------------------------------------
    # Event Handlers (@handles)
    # -----------------------------------------------------------------------

    @handles(HomebrewRuleRegistered)
    def _on_homebrew_registered(self, event: HomebrewRuleRegistered) -> None:
        self.state.homebrew_rules[str(event.rule_id)] = {
            "rule_id": str(event.rule_id),
            "campaign_id": str(event.campaign_id),
            "author_id": event.author_id,
            "rule_type": event.rule_type,
            "title": event.title,
            "content": event.content,
            "metadata": event.metadata,
        }


class EncounterState(BaseModel):
    """Internal state representation for an encounter computation."""

    encounter_id: UUID
    campaign_id: UUID | None = None
    party_levels: list[int] = Field(default_factory=list)
    target_difficulty: str = "Medium"
    total_party_xp_threshold: dict[str, int] = Field(default_factory=dict)
    selected_monsters: list[dict[str, Any]] = Field(default_factory=list)
    total_xp: int = 0
    adjusted_xp: int = 0
    difficulty_tier: str = "Medium"
    multiplier: float = 1.0


class EncounterAggregate(DeclarativeAggregate[EncounterState]):
    """Event-sourced aggregate managing combat encounter balancing decisions."""

    aggregate_type = "Encounter"
    requires_creation_event = True

    def record_balanced_encounter(
        self,
        encounter_id: UUID,
        party_levels: list[int],
        target_difficulty: str,
        total_party_xp_threshold: dict[str, int],
        selected_monsters: list[dict[str, Any]],
        total_xp: int,
        adjusted_xp: int,
        difficulty_tier: str,
        multiplier: float,
        campaign_id: UUID | None = None,
    ) -> None:
        """Record an encounter balanced calculation."""
        self.create_event(
            EncounterBalanced,
            aggregate_id=self.aggregate_id,
            encounter_id=encounter_id,
            campaign_id=campaign_id,
            party_levels=party_levels,
            target_difficulty=target_difficulty,
            total_party_xp_threshold=total_party_xp_threshold,
            selected_monsters=selected_monsters,
            total_xp=total_xp,
            adjusted_xp=adjusted_xp,
            difficulty_tier=difficulty_tier,
            multiplier=multiplier,
        )

    # -----------------------------------------------------------------------
    # Event Handlers (@handles)
    # -----------------------------------------------------------------------

    @handles(EncounterBalanced)
    def _on_encounter_balanced(self, event: EncounterBalanced) -> None:
        self._state = EncounterState(
            encounter_id=event.encounter_id,
            campaign_id=event.campaign_id,
            party_levels=event.party_levels,
            target_difficulty=event.target_difficulty,
            total_party_xp_threshold=event.total_party_xp_threshold,
            selected_monsters=event.selected_monsters,
            total_xp=event.total_xp,
            adjusted_xp=event.adjusted_xp,
            difficulty_tier=event.difficulty_tier,
            multiplier=event.multiplier,
        )
