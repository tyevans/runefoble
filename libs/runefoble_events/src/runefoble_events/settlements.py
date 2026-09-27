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


SettlementChartered = SettlementCharteredEvent
SettlementUpgraded = SettlementUpgradedEvent
SettlementRestBoonClaimed = SettlementRestBoonClaimedEvent

__all__ = [
    "SettlementChartered",
    "SettlementCharteredEvent",
    "SettlementRestBoonClaimed",
    "SettlementRestBoonClaimedEvent",
    "SettlementUpgraded",
    "SettlementUpgradedEvent",
]
