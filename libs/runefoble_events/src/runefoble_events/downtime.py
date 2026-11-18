"""Downtime, crafting, and stronghold events for Runefoble, built on eventsource-py."""

from typing import Any, ClassVar
from uuid import UUID

from pydantic import Field

from runefoble_events.base import BaseRunefobleEvent, register_event


@register_event("runefoble.events.downtime.crafting_attempted")
class CraftingAttempted(BaseRunefobleEvent):
    """Fired when an artisan initiates alchemical or mechanical combination."""

    suppress_event_type_warning: ClassVar[bool] = True
    event_type: str = "runefoble.events.downtime.crafting_attempted"

    aggregate_type: str = "Crafting"
    character_id: UUID
    player_id: str | None = None
    campaign_id: UUID | None = None
    session_id: UUID | None = None
    reagents: list[str] = Field(default_factory=list)
    catalyst: str | None = None
    risk_score: float = 0.0


@register_event("runefoble.events.downtime.crafting_succeeded")
class CraftingSucceeded(BaseRunefobleEvent):
    """Fired when reagents transmute successfully into a potion, pellet, or artifact."""

    suppress_event_type_warning: ClassVar[bool] = True
    event_type: str = "runefoble.events.downtime.crafting_succeeded"

    aggregate_type: str = "Crafting"
    character_id: UUID
    campaign_id: UUID | None = None
    session_id: UUID | None = None
    recipe_name: str
    item_name: str
    quantity: int = 1
    tags: list[str] = Field(default_factory=list)
    reagents_consumed: list[str] = Field(default_factory=list)
    catalyst_consumed: str | None = None
    properties: dict[str, Any] = Field(default_factory=dict)


@register_event("runefoble.events.downtime.crafting_mishap_occurred")
class CraftingMishapOccurred(BaseRunefobleEvent):
    """Fired when volatile reagents react catastrophically."""

    suppress_event_type_warning: ClassVar[bool] = True
    event_type: str = "runefoble.events.downtime.crafting_mishap_occurred"

    aggregate_type: str = "Crafting"
    character_id: UUID
    campaign_id: UUID | None = None
    session_id: UUID | None = None
    mishap_type: str
    severity: str = "minor"
    description: str
    damage_dealt: int = 0
    condition_inflicted: str | None = None
    reagents_lost: list[str] = Field(default_factory=list)


@register_event("runefoble.events.downtime.campfire_rest_completed")
class CampfireRestCompleted(BaseRunefobleEvent):
    """Fired when a party finishes resting around the campfire interlude."""

    suppress_event_type_warning: ClassVar[bool] = True
    event_type: str = "runefoble.events.downtime.campfire_rest_completed"

    aggregate_type: str = "GameSession"
    session_id: UUID | str | None = None
    campaign_id: UUID | None = None
    rest_type: str = "long"
    storytelling_prompt: str
    boons_applied: list[str] = Field(default_factory=list)
    participants_healed: list[str] = Field(default_factory=list)


@register_event("runefoble.events.downtime.stronghold_created")
class StrongholdCreated(BaseRunefobleEvent):
    """Fired when a persistent campsite or base is established."""

    suppress_event_type_warning: ClassVar[bool] = True
    event_type: str = "runefoble.events.downtime.stronghold_created"

    aggregate_type: str = "Stronghold"
    campaign_id: UUID | None = None
    name: str = "Party Campsite"
    location: str = "Wilderness"


@register_event("runefoble.events.downtime.stronghold_upgraded")
class StrongholdUpgraded(BaseRunefobleEvent):
    """Fired when gold or materials are invested into camp facilities."""

    suppress_event_type_warning: ClassVar[bool] = True
    event_type: str = "runefoble.events.downtime.stronghold_upgraded"

    aggregate_type: str = "Stronghold"
    campaign_id: UUID | None = None
    facility_id: str
    new_tier: int
    gold_spent: int = 0
    materials_spent: dict[str, int] = Field(default_factory=dict)
    unlocked_boons: list[str] = Field(default_factory=list)


@register_event("runefoble.events.downtime.stronghold_deposited")
class StrongholdDeposited(BaseRunefobleEvent):
    """Fired when gold or materials are added to the stronghold treasury and store."""

    suppress_event_type_warning: ClassVar[bool] = True
    event_type: str = "runefoble.events.downtime.stronghold_deposited"

    aggregate_type: str = "Stronghold"
    campaign_id: UUID | None = None
    gold: int = 0
    materials: dict[str, int] = Field(default_factory=dict)


@register_event("runefoble.events.downtime.stronghold_treasury_contributed")
class StrongholdTreasuryContributed(BaseRunefobleEvent):
    """Fired when gold leaves the stronghold treasury to fund a frontier outpost (TASK-0795)."""

    suppress_event_type_warning: ClassVar[bool] = True
    event_type: str = "runefoble.events.downtime.stronghold_treasury_contributed"

    aggregate_type: str = "Stronghold"
    campaign_id: UUID | None = None
    gold: int = 0
    destination_outpost_id: str = ""


__all__ = [
    "CampfireRestCompleted",
    "CraftingAttempted",
    "CraftingMishapOccurred",
    "CraftingSucceeded",
    "StrongholdCreated",
    "StrongholdDeposited",
    "StrongholdTreasuryContributed",
    "StrongholdUpgraded",
]
