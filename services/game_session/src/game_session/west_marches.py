"""West Marches shared persistent world state aggregate.

Part of TASK-0127 / PRD-0007 / US-0058 / ADR-0001 / ADR-0006 / ADR-0011.
Governed by Hard Invariant 2: Domain state changes flow strictly through
DeclarativeAggregate subclasses with @handles methods.
"""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Any
from uuid import UUID, uuid4

from eventsource.domain.aggregate import DeclarativeAggregate
from eventsource.domain.decorators import handles
from game_session.caravan_ledger import CaravanLedgerAggregate, CaravanLedgerState
from pydantic import BaseModel, Field
from runefoble_events.west_marches import (
    CampaignRegisteredToSharedWorld,
    CommunalNoticePosted,
    CrossCampaignDiscoveryShared,
    OutpostEstablished,
    SharedStrongholdUpgraded,
    SharedWorldCreated,
)


def _to_uuid(val: Any) -> UUID | None:
    if not val:
        return None
    try:
        return UUID(str(val))
    except Exception:
        return None


class SharedWorldState(BaseModel):
    """Event-sourced state for persistent West Marches shared frontier."""

    shared_world_id: str = ""
    name: str = "The Frontier Marches"
    frontier_region: str = "The Untamed Wilds"
    description: str = ""
    created_by: str = "system"
    registered_campaigns: dict[str, str] = Field(default_factory=dict)
    discoveries: list[dict[str, Any]] = Field(default_factory=list)
    outposts: dict[str, dict[str, Any]] = Field(default_factory=dict)
    tavern_board: list[dict[str, Any]] = Field(default_factory=list)


class SharedWorldAggregate(DeclarativeAggregate[SharedWorldState]):
    """Event-sourced aggregate managing multi-party frontier discoveries, outposts, and notices."""

    aggregate_type = "SharedWorld"
    requires_creation_event = False

    def __init__(self, aggregate_id: Any = None, **kwargs: Any) -> None:
        super().__init__(aggregate_id=aggregate_id, **kwargs)
        if self._state is None:
            self._state = SharedWorldState(shared_world_id=str(aggregate_id or ""))

    @handles(SharedWorldCreated)
    def handle_created(self, event: SharedWorldCreated) -> None:
        self._state = SharedWorldState(
            shared_world_id=str(event.shared_world_id),
            name=event.name,
            frontier_region=event.frontier_region,
            description=event.description,
            created_by=event.created_by,
        )

    @handles(CampaignRegisteredToSharedWorld)
    def handle_campaign_registered(self, event: CampaignRegisteredToSharedWorld) -> None:
        self.state.registered_campaigns[str(event.campaign_id)] = event.party_name

    @handles(CrossCampaignDiscoveryShared)
    def handle_discovery_shared(self, event: CrossCampaignDiscoveryShared) -> None:
        discovery_entry = {
            "discovery_id": event.discovery_id,
            "name": event.name,
            "discovery_type": event.discovery_type,
            "coordinates": event.coordinates,
            "discovered_by_campaign_id": str(event.discovered_by_campaign_id),
            "discovered_by_party_name": event.discovered_by_party_name,
            "description": event.description,
            "danger_level": event.danger_level,
            "metadata": event.metadata,
            "timestamp": event.occurred_at.isoformat()
            if hasattr(event, "occurred_at") and event.occurred_at
            else datetime.now(UTC).isoformat(),
        }
        self.state.discoveries = [
            d for d in self.state.discoveries if d["discovery_id"] != event.discovery_id
        ]
        self.state.discoveries.append(discovery_entry)

    @handles(OutpostEstablished)
    def handle_outpost_established(self, event: OutpostEstablished) -> None:
        self.state.outposts[event.outpost_id] = {
            "outpost_id": event.outpost_id,
            "name": event.name,
            "region": event.region,
            "level": event.level,
            "facilities": event.facilities,
            "contributing_campaigns": [str(event.contributing_campaign_id)],
            "stored_resources": dict(event.resources_contributed),
        }

    @handles(SharedStrongholdUpgraded)
    def handle_outpost_upgraded(self, event: SharedStrongholdUpgraded) -> None:
        if event.outpost_id in self.state.outposts:
            outpost = self.state.outposts[event.outpost_id]
            outpost["facilities"][event.facility_id] = event.new_tier
            cid = str(event.contributing_campaign_id)
            if cid and cid not in outpost["contributing_campaigns"]:
                outpost["contributing_campaigns"].append(cid)
            for mat, qty in event.materials_spent.items():
                outpost["stored_resources"][mat] = outpost["stored_resources"].get(mat, 0) + qty

    @handles(CommunalNoticePosted)
    def handle_notice_posted(self, event: CommunalNoticePosted) -> None:
        notice = {
            "notice_id": event.notice_id,
            "campaign_id": str(event.campaign_id),
            "author_name": event.author_name,
            "title": event.title,
            "content": event.content,
            "notice_type": event.notice_type,
            "bounty_reward": event.bounty_reward,
            "posted_at": datetime.now(UTC).isoformat(),
        }
        self.state.tavern_board.append(notice)

    def create_shared_world(
        self,
        name: str,
        frontier_region: str,
        description: str = "",
        created_by: str = "system",
    ) -> None:
        wid = _to_uuid(self.aggregate_id) or uuid4()
        self.create_event(
            SharedWorldCreated,
            shared_world_id=wid,
            name=name,
            frontier_region=frontier_region,
            description=description,
            created_by=created_by,
        )

    def register_campaign(
        self,
        campaign_id: UUID | str,
        party_name: str,
        registered_by: str = "guild_officer",
    ) -> None:
        wid = _to_uuid(self.state.shared_world_id or self.aggregate_id)
        cid = _to_uuid(campaign_id) or str(campaign_id)
        self.create_event(
            CampaignRegisteredToSharedWorld,
            shared_world_id=wid,
            campaign_id=cid,
            party_name=party_name,
            registered_by=registered_by,
        )

    def record_discovery(
        self,
        name: str,
        discovery_type: str,
        coordinates: dict[str, float],
        discovered_by_campaign_id: UUID | str,
        discovered_by_party_name: str,
        description: str = "",
        danger_level: int = 1,
        discovery_id: str | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> str:
        did = discovery_id or f"disc_{uuid4().hex[:10]}"
        wid = _to_uuid(self.state.shared_world_id or self.aggregate_id)
        cid = _to_uuid(discovered_by_campaign_id) or str(discovered_by_campaign_id)
        self.create_event(
            CrossCampaignDiscoveryShared,
            shared_world_id=wid,
            discovery_id=did,
            name=name,
            discovery_type=discovery_type,
            coordinates=coordinates,
            discovered_by_campaign_id=cid,
            discovered_by_party_name=discovered_by_party_name,
            description=description,
            danger_level=danger_level,
            metadata=metadata or {},
        )
        return did

    def establish_outpost(
        self,
        name: str,
        region: str,
        contributing_campaign_id: UUID | str,
        outpost_id: str | None = None,
        facilities: dict[str, int] | None = None,
        resources_contributed: dict[str, int] | None = None,
    ) -> str:
        oid = outpost_id or f"outpost_{uuid4().hex[:8]}"
        wid = _to_uuid(self.state.shared_world_id or self.aggregate_id)
        cid = _to_uuid(contributing_campaign_id) or str(contributing_campaign_id)
        self.create_event(
            OutpostEstablished,
            shared_world_id=wid,
            outpost_id=oid,
            name=name,
            region=region,
            level=1,
            facilities=facilities or {"trading_post": 1, "watchtower": 1},
            contributing_campaign_id=cid,
            resources_contributed=resources_contributed or {},
        )
        return oid

    def upgrade_outpost(
        self,
        outpost_id: str,
        facility_id: str,
        contributing_campaign_id: UUID | str,
        gold_spent: int = 0,
        materials_spent: dict[str, int] | None = None,
    ) -> int:
        if outpost_id not in self.state.outposts:
            raise ValueError(f"Outpost '{outpost_id}' does not exist")
        current_tier = self.state.outposts[outpost_id]["facilities"].get(facility_id, 0)
        next_tier = current_tier + 1
        wid = _to_uuid(self.state.shared_world_id or self.aggregate_id)
        cid = _to_uuid(contributing_campaign_id) or str(contributing_campaign_id)
        self.create_event(
            SharedStrongholdUpgraded,
            shared_world_id=wid,
            outpost_id=outpost_id,
            facility_id=facility_id,
            new_tier=next_tier,
            contributing_campaign_id=cid,
            gold_spent=gold_spent,
            materials_spent=materials_spent or {},
        )
        return next_tier

    def post_communal_notice(
        self,
        campaign_id: UUID | str,
        author_name: str,
        title: str,
        content: str,
        notice_type: str = "bounty",
        bounty_reward: int | str = 0,
        notice_id: str | None = None,
    ) -> str:
        nid = notice_id or f"notice_{uuid4().hex[:8]}"
        wid = _to_uuid(self.state.shared_world_id or self.aggregate_id)
        cid = _to_uuid(campaign_id) or str(campaign_id)
        self.create_event(
            CommunalNoticePosted,
            shared_world_id=wid,
            notice_id=nid,
            campaign_id=cid,
            author_name=author_name,
            title=title,
            content=content,
            notice_type=notice_type,
            bounty_reward=bounty_reward,
        )
        return nid


__all__ = [
    "CaravanLedgerAggregate",
    "CaravanLedgerState",
    "SharedWorldAggregate",
    "SharedWorldState",
]
