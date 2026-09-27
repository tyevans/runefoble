"""Event-sourced aggregate for West Marches shared frontier and communal stronghold.

Part of TASK-0135 / PRD-0007 / PRD-0014 / US-0050 / US-0058 / ADR-0001 / ADR-0011.
Governed by Hard Invariant 2 (eventsource-py DeclarativeAggregate).
"""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Any
from uuid import UUID, uuid4

from eventsource.domain.aggregate import DeclarativeAggregate
from eventsource.domain.decorators import handles
from pydantic import BaseModel, Field
from runefoble_events.west_marches import (
    CampaignRegisteredToSharedWorld,
    CommunalNoticePosted,
    CrossCampaignDiscoveryShared,
    OutpostEstablished,
    SharedStrongholdUpgraded,
    SharedWorldCreated,
)

FACILITY_BOONS: dict[str, dict[int, str]] = {
    "alchemical_workshop": {
        1: "Reagent Extraction (+1 Herbal Reagent)",
        2: "Enhanced Potion Yield (+1 Potion)",
        3: "Volatile Mishap Immunity",
    },
    "watchtower": {
        1: "Early Warning (+1 Initiative)",
        2: "Scouting Advantage (No Ambush)",
        3: "Regional Threat Detection",
    },
    "trading_post": {
        1: "Market Access",
        2: "Wholesale Discounts (10% Gold)",
        3: "Exotic Caravan Trading",
    },
    "arcane_forge": {
        1: "Apprentice Smithing",
        2: "Enchanted Weaponry (+1 Damage)",
        3: "Masterwork Artifice",
    },
    "herbal_rack": {
        1: "Campfire Herb Drying",
        2: "+2 HP Rest Recovery",
        3: "Restorative Salve Stock",
    },
}


def _to_uuid(val: Any) -> UUID | None:
    if not val:
        return None
    try:
        return UUID(str(val))
    except Exception:
        return None


class WestMarchesState(BaseModel):
    """Event-sourced state for West Marches shared world frontier and stronghold."""

    campaign_id: str = ""
    shared_world_id: str = ""
    world_name: str = "The Frontier Marches"
    frontier_region: str = "The Untamed Wilds"
    description: str = ""
    party_name: str = "Pioneers"
    registered_campaigns: dict[str, str] = Field(default_factory=dict)
    discoveries: list[dict[str, Any]] = Field(default_factory=list)
    outposts: dict[str, dict[str, Any]] = Field(default_factory=dict)
    tavern_board: list[dict[str, Any]] = Field(default_factory=list)


class WestMarchesAtlasAggregate(DeclarativeAggregate[WestMarchesState]):
    """Aggregate managing multi-party frontier discoveries, communal stronghold, and notices."""

    aggregate_type = "SharedWorld"
    requires_creation_event = False

    def __init__(self, aggregate_id: Any = None, **kwargs: Any) -> None:
        super().__init__(aggregate_id=aggregate_id, **kwargs)
        if self._state is None:
            self._state = WestMarchesState(
                campaign_id=str(aggregate_id or ""),
                shared_world_id=f"world_{str(aggregate_id or '')[:8]}",
            )
            # Default communal outpost
            default_outpost_id = f"outpost_{str(aggregate_id or '')[:8]}"
            self._state.outposts[default_outpost_id] = {
                "outpost_id": default_outpost_id,
                "name": "Communal Frontier Stronghold",
                "region": "The Untamed Wilds",
                "level": 1,
                "facilities": {
                    "alchemical_workshop": 1,
                    "watchtower": 1,
                    "trading_post": 1,
                },
                "contributing_campaigns": [str(aggregate_id or "")],
                "stored_resources": {"gold": 100, "timber": 20, "stone": 15},
                "boons": [
                    "Reagent Extraction (+1 Herbal Reagent)",
                    "Early Warning (+1 Initiative)",
                    "Market Access",
                ],
                "defensive_buffer": 15,
            }

    @handles(SharedWorldCreated)
    def handle_created(self, event: SharedWorldCreated) -> None:
        self._state.shared_world_id = str(event.shared_world_id)
        self._state.world_name = event.name
        self._state.frontier_region = event.frontier_region
        self._state.description = event.description

    @handles(CampaignRegisteredToSharedWorld)
    def handle_campaign_registered(self, event: CampaignRegisteredToSharedWorld) -> None:
        self._state.registered_campaigns[str(event.campaign_id)] = event.party_name
        if str(event.campaign_id) == self._state.campaign_id:
            self._state.party_name = event.party_name

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
        self._state.discoveries = [
            d for d in self._state.discoveries if d["discovery_id"] != event.discovery_id
        ]
        self._state.discoveries.append(discovery_entry)

    @handles(OutpostEstablished)
    def handle_outpost_established(self, event: OutpostEstablished) -> None:
        facilities = event.facilities or {"watchtower": 1, "trading_post": 1}
        boons = self._calculate_boons(facilities)
        defense = facilities.get("watchtower", 0) * 10 + event.level * 5
        self._state.outposts[event.outpost_id] = {
            "outpost_id": event.outpost_id,
            "name": event.name,
            "region": event.region,
            "level": event.level,
            "facilities": facilities,
            "contributing_campaigns": [str(event.contributing_campaign_id)],
            "stored_resources": dict(event.resources_contributed or {}),
            "boons": boons,
            "defensive_buffer": defense,
        }

    @handles(SharedStrongholdUpgraded)
    def handle_outpost_upgraded(self, event: SharedStrongholdUpgraded) -> None:
        if event.outpost_id in self._state.outposts:
            outpost = self._state.outposts[event.outpost_id]
            outpost["facilities"][event.facility_id] = event.new_tier
            cid = str(event.contributing_campaign_id)
            if cid and cid not in outpost["contributing_campaigns"]:
                outpost["contributing_campaigns"].append(cid)
            for mat, qty in event.materials_spent.items():
                outpost["stored_resources"][mat] = outpost["stored_resources"].get(mat, 0) + qty
            outpost["boons"] = self._calculate_boons(outpost["facilities"])
            outpost["defensive_buffer"] = (
                outpost["facilities"].get("watchtower", 0) * 10 + outpost.get("level", 1) * 5
            )

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
        self._state.tavern_board.append(notice)

    def _calculate_boons(self, facilities: dict[str, int]) -> list[str]:
        boons: list[str] = []
        for fac, tier in facilities.items():
            if fac in FACILITY_BOONS:
                for t in range(1, tier + 1):
                    if t in FACILITY_BOONS[fac]:
                        boons.append(FACILITY_BOONS[fac][t])
        return boons

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
        wid = _to_uuid(self._state.shared_world_id) or uuid4()
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

    def upgrade_outpost(
        self,
        outpost_id: str,
        facility_id: str,
        contributing_campaign_id: UUID | str,
        gold_spent: int = 0,
        materials_spent: dict[str, int] | None = None,
    ) -> int:
        if outpost_id not in self._state.outposts:
            # Fall back to first available outpost or create one
            if self._state.outposts:
                outpost_id = next(iter(self._state.outposts.keys()))
            else:
                outpost_id = f"outpost_{uuid4().hex[:8]}"
                self._state.outposts[outpost_id] = {
                    "outpost_id": outpost_id,
                    "name": "Communal Stronghold",
                    "region": self._state.frontier_region,
                    "level": 1,
                    "facilities": {},
                    "contributing_campaigns": [str(contributing_campaign_id)],
                    "stored_resources": {},
                    "boons": [],
                    "defensive_buffer": 10,
                }
        current_tier = self._state.outposts[outpost_id]["facilities"].get(facility_id, 0)
        next_tier = current_tier + 1
        wid = _to_uuid(self._state.shared_world_id) or uuid4()
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
        wid = _to_uuid(self._state.shared_world_id) or uuid4()
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
    "FACILITY_BOONS",
    "WestMarchesAtlasAggregate",
    "WestMarchesState",
]
