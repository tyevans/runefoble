"""West Marches shared world state and cross-campaign trading events."""

from __future__ import annotations

from typing import Any, ClassVar
from uuid import UUID

from pydantic import Field

from runefoble_events.base import BaseRunefobleEvent, register_event


@register_event("runefoble.events.west_marches.shared_world_created")
class SharedWorldCreated(BaseRunefobleEvent):
    """Fired when a persistent West Marches shared world frontier is established."""

    suppress_event_type_warning: ClassVar[bool] = True
    event_type: str = "runefoble.events.west_marches.shared_world_created"

    aggregate_type: str = "SharedWorld"
    shared_world_id: UUID | str = ""
    name: str = "The Frontier Marches"
    frontier_region: str = "The Untamed Wilds"
    description: str = ""
    created_by: str = "system"


@register_event("runefoble.events.west_marches.campaign_registered_to_shared_world")
class CampaignRegisteredToSharedWorld(BaseRunefobleEvent):
    """Fired when an adventuring campaign links into a shared world frontier."""

    suppress_event_type_warning: ClassVar[bool] = True
    event_type: str = "runefoble.events.west_marches.campaign_registered_to_shared_world"

    aggregate_type: str = "SharedWorld"
    shared_world_id: UUID | str = ""
    campaign_id: UUID | str = ""
    party_name: str = ""
    registered_by: str = "guild_officer"


@register_event("runefoble.events.west_marches.cross_campaign_discovery_shared")
class CrossCampaignDiscoveryShared(BaseRunefobleEvent):
    """Fired when an adventuring party maps a point of interest, dungeon, or waypoint."""

    suppress_event_type_warning: ClassVar[bool] = True
    event_type: str = "runefoble.events.west_marches.cross_campaign_discovery_shared"

    aggregate_type: str = "SharedWorld"
    shared_world_id: UUID | str = ""
    discovery_id: str = ""
    name: str = ""
    discovery_type: str = "dungeon"
    coordinates: dict[str, float] = Field(default_factory=dict)
    discovered_by_campaign_id: UUID | str = ""
    discovered_by_party_name: str = ""
    description: str = ""
    danger_level: int = 1
    metadata: dict[str, Any] = Field(default_factory=dict)


@register_event("runefoble.events.west_marches.outpost_established")
class OutpostEstablished(BaseRunefobleEvent):
    """Fired when a regional settlement or base camp is established."""

    suppress_event_type_warning: ClassVar[bool] = True
    event_type: str = "runefoble.events.west_marches.outpost_established"

    aggregate_type: str = "SharedWorld"
    shared_world_id: UUID | str = ""
    outpost_id: str = ""
    name: str = ""
    region: str = ""
    level: int = 1
    facilities: dict[str, int] = Field(default_factory=dict)
    contributing_campaign_id: UUID | str = ""
    resources_contributed: dict[str, int] = Field(default_factory=dict)


@register_event("runefoble.events.west_marches.shared_stronghold_upgraded")
class SharedStrongholdUpgraded(BaseRunefobleEvent):
    """Fired when communal outpost facilities are upgraded."""

    suppress_event_type_warning: ClassVar[bool] = True
    event_type: str = "runefoble.events.west_marches.shared_stronghold_upgraded"

    aggregate_type: str = "SharedWorld"
    shared_world_id: UUID | str = ""
    outpost_id: str = ""
    facility_id: str = ""
    new_tier: int = 1
    contributing_campaign_id: UUID | str = ""
    gold_spent: int = 0
    materials_spent: dict[str, int] = Field(default_factory=dict)


@register_event("runefoble.events.west_marches.outpost_resources_contributed")
class OutpostResourcesContributed(BaseRunefobleEvent):
    """Fired when a contributing campaign funds an outpost store (TASK-0795).

    The gold comes from the campaign stronghold treasury. The debit is a separate event
    in game_session (`StrongholdTreasuryContributed`).
    """

    suppress_event_type_warning: ClassVar[bool] = True
    event_type: str = "runefoble.events.west_marches.outpost_resources_contributed"

    aggregate_type: str = "SharedWorld"
    shared_world_id: UUID | str = ""
    outpost_id: str = ""
    contributing_campaign_id: UUID | str = ""
    gold: int = 0
    materials: dict[str, int] = Field(default_factory=dict)


@register_event("runefoble.events.west_marches.communal_notice_posted")
class CommunalNoticePosted(BaseRunefobleEvent):
    """Fired when a cross-campaign notice or bounty is posted to the tavern board."""

    suppress_event_type_warning: ClassVar[bool] = True
    event_type: str = "runefoble.events.west_marches.communal_notice_posted"

    aggregate_type: str = "SharedWorld"
    shared_world_id: UUID | str = ""
    notice_id: str = ""
    campaign_id: UUID | str = ""
    author_name: str = ""
    title: str = ""
    content: str = ""
    notice_type: str = "bounty"
    bounty_reward: int | str = 0


@register_event("runefoble.events.west_marches.caravan_contract_posted")
class CaravanContractPosted(BaseRunefobleEvent):
    """Fired when an asynchronous mercenary caravan contract is posted."""

    suppress_event_type_warning: ClassVar[bool] = True
    event_type: str = "runefoble.events.west_marches.caravan_contract_posted"

    aggregate_type: str = "CaravanContract"
    contract_id: str = ""
    shared_world_id: UUID | str = ""
    origin_outpost: str = ""
    destination_outpost: str = ""
    cargo: dict[str, int] = Field(default_factory=dict)
    cargo_value: int = 0
    route_risk_level: str = "medium"
    transit_stages: int = 2
    escort_collateral: int = 0
    reward_gold: int = 0
    reward_reputation: int = 0
    posted_by_campaign_id: UUID | str = ""
    poster_user_id: str | None = None
    expires_in_turns: int = 10
    status: str = "open"
    created_at: str | None = None


@register_event("runefoble.events.west_marches.caravan_contract_accepted")
class CaravanContractAccepted(BaseRunefobleEvent):
    """Fired when an adventuring party claims or accepts an escort contract."""

    suppress_event_type_warning: ClassVar[bool] = True
    event_type: str = "runefoble.events.west_marches.caravan_contract_accepted"

    aggregate_type: str = "CaravanContract"
    contract_id: str = ""
    shared_world_id: UUID | str = ""
    contractor_campaign_id: UUID | str = ""
    contractor_party_name: str = ""
    accepted_by_user_id: str | None = None
    status: str = "accepted"
    accepted_at: str | None = None


@register_event("runefoble.events.west_marches.caravan_dispatched")
class CaravanDispatched(BaseRunefobleEvent):
    """Fired when a resource caravan sets off across the frontier."""

    suppress_event_type_warning: ClassVar[bool] = True
    event_type: str = "runefoble.events.west_marches.caravan_dispatched"

    aggregate_type: str = ""
    contract_id: str | None = None
    shared_world_id: UUID | str = ""
    caravan_id: str = ""
    origin_outpost: str = ""
    destination_outpost: str = ""
    cargo: dict[str, int] = Field(default_factory=dict)
    dispatched_by_campaign_id: UUID | str = ""
    transit_turns: int = 1
    status: str = "in_transit"


@register_event("runefoble.events.west_marches.caravan_ambushed")
class CaravanAmbushed(BaseRunefobleEvent):
    """Fired when a caravan encounters a wilderness hazard or ambush during transit."""

    suppress_event_type_warning: ClassVar[bool] = True
    event_type: str = "runefoble.events.west_marches.caravan_ambushed"

    aggregate_type: str = "CaravanContract"
    contract_id: str = ""
    shared_world_id: UUID | str = ""
    caravan_id: str = ""
    stage_index: int = 1
    ambush_type: str = "bandit_raid"
    danger_level: int = 1
    outcome: str = "repelled"
    cargo_loss_percentage: float = 0.0
    reported_by_campaign_id: UUID | str = ""
    notes: str = ""


@register_event("runefoble.events.west_marches.caravan_trade_fulfilled")
class CaravanTradeFulfilled(BaseRunefobleEvent):
    """Fired when a caravan reaches destination, delivering cargo and completing the contract."""

    suppress_event_type_warning: ClassVar[bool] = True
    event_type: str = "runefoble.events.west_marches.caravan_trade_fulfilled"

    aggregate_type: str = "CaravanContract"
    contract_id: str = ""
    shared_world_id: UUID | str = ""
    caravan_id: str = ""
    origin_outpost: str = ""
    destination_outpost: str = ""
    cargo_delivered: dict[str, int] = Field(default_factory=dict)
    cargo_value_delivered: int = 0
    reward_gold_paid: int = 0
    reputation_awarded: int = 0
    contractor_campaign_id: UUID | str = ""
    fulfilled_at: str | None = None
    status: str = "fulfilled"


@register_event("runefoble.events.west_marches.caravan_trade_completed")
class CaravanTradeCompleted(BaseRunefobleEvent):
    """Fired when a caravan arrives at its destination outpost, delivering cargo."""

    suppress_event_type_warning: ClassVar[bool] = True
    event_type: str = "runefoble.events.west_marches.caravan_trade_completed"

    aggregate_type: str = "CaravanLedger"
    shared_world_id: UUID | str = ""
    caravan_id: str = ""
    origin_outpost: str = ""
    destination_outpost: str = ""
    cargo_delivered: dict[str, int] = Field(default_factory=dict)
    unlocked_stock: dict[str, Any] = Field(default_factory=dict)
    completed_at: str | None = None


@register_event("runefoble.events.west_marches.regional_merchant_stock_updated")
class RegionalMerchantStockUpdated(BaseRunefobleEvent):
    """Fired when outpost merchant inventory adjusts due to trade or expeditions."""

    suppress_event_type_warning: ClassVar[bool] = True
    event_type: str = "runefoble.events.west_marches.regional_merchant_stock_updated"

    aggregate_type: str = "CaravanLedger"
    shared_world_id: UUID | str = ""
    outpost_name: str = ""
    inventory_updates: dict[str, Any] = Field(default_factory=dict)


__all__ = [
    "CampaignRegisteredToSharedWorld",
    "CaravanAmbushed",
    "CaravanContractAccepted",
    "CaravanContractPosted",
    "CaravanDispatched",
    "CaravanTradeCompleted",
    "CaravanTradeFulfilled",
    "CommunalNoticePosted",
    "CrossCampaignDiscoveryShared",
    "OutpostEstablished",
    "OutpostResourcesContributed",
    "RegionalMerchantStockUpdated",
    "SharedStrongholdUpgraded",
    "SharedWorldCreated",
]
