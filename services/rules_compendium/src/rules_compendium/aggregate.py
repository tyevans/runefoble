"""Event-sourced Compendium and Encounter aggregates using eventsource-py."""

from typing import Any
from uuid import UUID

from eventsource.domain.aggregate import DeclarativeAggregate
from eventsource.domain.decorators import handles
from pydantic import BaseModel, Field
from runefoble_events.compendium import (
    ConditionIndexed,
    EncounterBalanced,
    HomebrewRuleRegistered,
    MonsterIndexed,
    SpellIndexed,
)


class CompendiumState(BaseModel):
    """Internal state representation for rules compendium index."""

    compendium_id: UUID
    monsters: dict[str, dict[str, Any]] = Field(default_factory=dict)
    spells: dict[str, dict[str, Any]] = Field(default_factory=dict)
    conditions: dict[str, dict[str, Any]] = Field(default_factory=dict)
    homebrew_rules: dict[str, dict[str, Any]] = Field(default_factory=dict)


class CompendiumAggregate(DeclarativeAggregate[CompendiumState]):
    """Event-sourced aggregate managing canonical rules and homebrew registration."""

    aggregate_type = "Compendium"
    requires_creation_event = False

    def init_state(self) -> CompendiumState:
        return CompendiumState(compendium_id=self.aggregate_id)

    def index_monster(
        self,
        monster_id: UUID,
        name: str,
        challenge_rating: float,
        creature_type: str,
        armor_class: int,
        hit_points: int,
        xp: int,
        role: str = "brute",
        size: str = "Medium",
        metadata: dict[str, Any] | None = None,
    ) -> None:
        """Index a monster stat block."""
        self.create_event(
            MonsterIndexed,
            aggregate_id=self.aggregate_id,
            monster_id=monster_id,
            name=name,
            challenge_rating=challenge_rating,
            creature_type=creature_type,
            size=size,
            armor_class=armor_class,
            hit_points=hit_points,
            xp=xp,
            role=role,
            metadata=metadata or {},
        )

    def index_spell(
        self,
        spell_id: UUID,
        name: str,
        level: int,
        school: str,
        casting_time: str,
        range_: str,
        components: str,
        duration: str,
        description: str,
        metadata: dict[str, Any] | None = None,
    ) -> None:
        """Index a spell definition."""
        self.create_event(
            SpellIndexed,
            aggregate_id=self.aggregate_id,
            spell_id=spell_id,
            name=name,
            level=level,
            school=school,
            casting_time=casting_time,
            range=range_,
            components=components,
            duration=duration,
            description=description,
            metadata=metadata or {},
        )

    def index_condition(
        self,
        condition_id: UUID,
        name: str,
        description: str,
        effects: list[str],
        metadata: dict[str, Any] | None = None,
    ) -> None:
        """Index a condition rule."""
        self.create_event(
            ConditionIndexed,
            aggregate_id=self.aggregate_id,
            condition_id=condition_id,
            name=name,
            description=description,
            effects=effects,
            metadata=metadata or {},
        )

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

    @handles(MonsterIndexed)
    def _on_monster_indexed(self, event: MonsterIndexed) -> None:
        if self._state is None:
            self._state = self.init_state()
        self.state.monsters[event.name.lower()] = {
            "monster_id": str(event.monster_id),
            "name": event.name,
            "challenge_rating": event.challenge_rating,
            "creature_type": event.creature_type,
            "size": event.size,
            "armor_class": event.armor_class,
            "hit_points": event.hit_points,
            "xp": event.xp,
            "role": event.role,
            "metadata": event.metadata,
        }

    @handles(SpellIndexed)
    def _on_spell_indexed(self, event: SpellIndexed) -> None:
        if self._state is None:
            self._state = self.init_state()
        self.state.spells[event.name.lower()] = {
            "spell_id": str(event.spell_id),
            "name": event.name,
            "level": event.level,
            "school": event.school,
            "casting_time": event.casting_time,
            "range": event.range,
            "components": event.components,
            "duration": event.duration,
            "description": event.description,
            "metadata": event.metadata,
        }

    @handles(ConditionIndexed)
    def _on_condition_indexed(self, event: ConditionIndexed) -> None:
        if self._state is None:
            self._state = self.init_state()
        self.state.conditions[event.name.lower()] = {
            "condition_id": str(event.condition_id),
            "name": event.name,
            "description": event.description,
            "effects": event.effects,
            "metadata": event.metadata,
        }

    @handles(HomebrewRuleRegistered)
    def _on_homebrew_registered(self, event: HomebrewRuleRegistered) -> None:
        if self._state is None:
            self._state = self.init_state()
        key = f"{event.campaign_id}:{event.title.lower()}"
        self.state.homebrew_rules[key] = {
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
