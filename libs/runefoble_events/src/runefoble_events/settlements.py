"""Domain events for frontier settlements, havens, workshops, and resting sanctums."""

from __future__ import annotations

from typing import Any, ClassVar
from uuid import UUID, uuid4

from pydantic import Field

from runefoble_events.base import BaseRunefobleEvent, register_event


@register_event("runefoble.events.game_session.settlement_chartered")
class SettlementCharteredEvent(BaseRunefobleEvent):
    """Fired when a new frontier outpost, haven, or fortress is chartered."""

    suppress_event_type_warning: ClassVar[bool] = True
    aggregate_type: str = "Settlement"
    aggregate_id: UUID = Field(default_factory=uuid4)
    event_type: str = "runefoble.events.game_session.settlement_chartered"
    settlement_id: str
    shared_world_id: str
    name: str
    settlement_type: str = "outpost"
    region: str = "Wilderness"
    coordinates: dict[str, float] = Field(default_factory=dict)
    founded_by_campaign_id: str = ""
    chartered_by: str = ""
    level: int = 1
    defense_rating: int = 10
    facilities: dict[str, int] = Field(default_factory=dict)
    metadata: dict[str, Any] = Field(default_factory=dict)


@register_event("runefoble.events.game_session.settlement_upgraded")
class SettlementUpgradedEvent(BaseRunefobleEvent):
    """Fired when a settlement facility or fortification is upgraded."""

    suppress_event_type_warning: ClassVar[bool] = True
    aggregate_type: str = "Settlement"
    aggregate_id: UUID = Field(default_factory=uuid4)
    event_type: str = "runefoble.events.game_session.settlement_upgraded"
    settlement_id: str
    shared_world_id: str
    facility_id: str
    new_tier: int
    tier_name: str = ""
    contributing_campaign_id: str = ""
    gold_spent: int = 0
    materials_spent: dict[str, int] = Field(default_factory=dict)
    defense_rating: int = 10
    metadata: dict[str, Any] = Field(default_factory=dict)


@register_event("runefoble.events.game_session.settlement_rest_boon_claimed")
class SettlementRestBoonClaimedEvent(BaseRunefobleEvent):
    """Fired when an adventuring party claims a rest or crafting boon from a haven facility."""

    suppress_event_type_warning: ClassVar[bool] = True
    aggregate_type: str = "Settlement"
    aggregate_id: UUID = Field(default_factory=uuid4)
    event_type: str = "runefoble.events.game_session.settlement_rest_boon_claimed"
    settlement_id: str
    shared_world_id: str
    campaign_id: str
    character_id: str = ""
    claimed_by: str = ""
    facility_id: str = "sanctum"
    boon: str = ""
    metadata: dict[str, Any] = Field(default_factory=dict)


@register_event("runefoble.events.game_session.settlement_founded")
class SettlementFoundedEvent(BaseRunefobleEvent):
    """Fired when a new settlement haven is founded with scale, biome, and layout."""

    suppress_event_type_warning: ClassVar[bool] = True
    aggregate_type: str = "Settlement"
    aggregate_id: UUID = Field(default_factory=uuid4)
    event_type: str = "runefoble.events.game_session.settlement_founded"
    settlement_id: str
    campaign_id: str
    name: str
    scale: str
    biome: str
    coordinates: dict[str, float] = Field(default_factory=dict)
    tier: int = 1
    prosperity: int = 0
    unlocked_districts: list[str] = Field(default_factory=list)
    founded_by: str = ""
    metadata: dict[str, Any] = Field(default_factory=dict)


@register_event("runefoble.events.game_session.settlement_tier_upgraded")
class SettlementTierUpgradedEvent(BaseRunefobleEvent):
    """Fired when a settlement advances to a higher civic scale tier."""

    suppress_event_type_warning: ClassVar[bool] = True
    aggregate_type: str = "Settlement"
    aggregate_id: UUID = Field(default_factory=uuid4)
    event_type: str = "runefoble.events.game_session.settlement_tier_upgraded"
    settlement_id: str
    old_tier: str | int
    new_tier: str | int
    unlocked_districts: list[str] = Field(default_factory=list)
    scale: str = ""
    prosperity: int = 0
    metadata: dict[str, Any] = Field(default_factory=dict)


@register_event("runefoble.events.game_session.establishment_constructed")
class EstablishmentConstructedEvent(BaseRunefobleEvent):
    """Fired when a new commercial, civic, or hospitality establishment is constructed."""

    suppress_event_type_warning: ClassVar[bool] = True
    aggregate_type: str = "Establishment"
    aggregate_id: UUID = Field(default_factory=uuid4)
    event_type: str = "runefoble.events.game_session.establishment_constructed"
    establishment_id: str
    settlement_id: str
    district_id: str
    category: str
    name: str
    campaign_id: str = ""
    tier: int = 1
    capacity: int = 10
    operating_cost: int = 5
    amenities: list[str] = Field(default_factory=list)
    owner_id: str = ""
    metadata: dict[str, Any] = Field(default_factory=dict)


@register_event("runefoble.events.game_session.establishment_upgraded")
class EstablishmentUpgradedEvent(BaseRunefobleEvent):
    """Fired when an establishment upgrades its facilities, capacity, or amenities."""

    suppress_event_type_warning: ClassVar[bool] = True
    aggregate_type: str = "Establishment"
    aggregate_id: UUID = Field(default_factory=uuid4)
    event_type: str = "runefoble.events.game_session.establishment_upgraded"
    establishment_id: str
    settlement_id: str = ""
    tier: int
    added_amenities: list[str] = Field(default_factory=list)
    capacity: int = 0
    operating_cost: int = 0
    metadata: dict[str, Any] = Field(default_factory=dict)


SettlementChartered = SettlementCharteredEvent
SettlementUpgraded = SettlementUpgradedEvent
SettlementRestBoonClaimed = SettlementRestBoonClaimedEvent
SettlementFounded = SettlementFoundedEvent
SettlementTierUpgraded = SettlementTierUpgradedEvent
EstablishmentConstructed = EstablishmentConstructedEvent
EstablishmentUpgraded = EstablishmentUpgradedEvent

__all__ = [
    "EstablishmentConstructed",
    "EstablishmentConstructedEvent",
    "EstablishmentUpgraded",
    "EstablishmentUpgradedEvent",
    "SettlementChartered",
    "SettlementCharteredEvent",
    "SettlementFounded",
    "SettlementFoundedEvent",
    "SettlementRestBoonClaimed",
    "SettlementRestBoonClaimedEvent",
    "SettlementTierUpgraded",
    "SettlementTierUpgradedEvent",
    "SettlementUpgraded",
    "SettlementUpgradedEvent",
]
