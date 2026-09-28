"""Event-sourced aggregate for West Marches shared frontier and communal stronghold.

Part of TASK-0135 / TASK-0205 / ADR-0003 / ADR-0007 / ADR-0011.
Governed by Hard Invariant 2 (eventsource-py) and Hard Invariant 6 (< 150 lines).
"""

from __future__ import annotations

from typing import Any
from uuid import UUID, uuid4

from eventsource.domain.aggregate import DeclarativeAggregate
from eventsource.domain.decorators import handles
from runefoble_events.west_marches import (
    CampaignRegisteredToSharedWorld,
    CommunalNoticePosted,
    CrossCampaignDiscoveryShared,
    OutpostEstablished,
    SharedStrongholdUpgraded,
    SharedWorldCreated,
)

from campaign_lore.models import WestMarchesState
from campaign_lore.west_marches_handlers import (
    FACILITY_BOONS,
    apply_discovery,
    apply_outpost_established,
    apply_outpost_upgraded,
    build_default_outpost,
    build_discovery_entry,
    build_notice_entry,
    calculate_boons,
)


def _to_uuid(val: Any) -> UUID | None:
    try:
        return UUID(str(val)) if val else None
    except Exception:
        return None


class WestMarchesAtlasAggregate(DeclarativeAggregate[WestMarchesState]):
    """Aggregate managing multi-party frontier discoveries, communal stronghold, and notices."""

    aggregate_type = "SharedWorld"
    requires_creation_event = False

    def __init__(self, aggregate_id: Any = None, **kwargs: Any) -> None:
        super().__init__(aggregate_id=aggregate_id, **kwargs)
        if self._state is None:
            cid = str(aggregate_id or "")
            self._state = WestMarchesState(campaign_id=cid, shared_world_id=f"world_{cid[:8]}")
            outpost = build_default_outpost(cid)
            self._state.outposts[outpost["outpost_id"]] = outpost

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
        self._state.discoveries = apply_discovery(
            self._state.discoveries, build_discovery_entry(event)
        )

    @handles(OutpostEstablished)
    def handle_outpost_established(self, event: OutpostEstablished) -> None:
        apply_outpost_established(self._state.outposts, event)

    @handles(SharedStrongholdUpgraded)
    def handle_outpost_upgraded(self, event: SharedStrongholdUpgraded) -> None:
        apply_outpost_upgraded(self._state.outposts, event)

    @handles(CommunalNoticePosted)
    def handle_notice_posted(self, event: CommunalNoticePosted) -> None:
        self._state.tavern_board.append(build_notice_entry(event))

    def record_discovery(self, **kwargs: Any) -> str:
        did = kwargs.get("discovery_id") or f"disc_{uuid4().hex[:10]}"
        wid = _to_uuid(self._state.shared_world_id) or uuid4()
        cid = _to_uuid(kwargs.get("discovered_by_campaign_id")) or str(
            kwargs.get("discovered_by_campaign_id", "")
        )
        self.create_event(
            CrossCampaignDiscoveryShared,
            **{
                **kwargs,
                "discovery_id": did,
                "shared_world_id": wid,
                "discovered_by_campaign_id": cid,
            },
        )
        return did

    def upgrade_outpost(self, outpost_id: str, facility_id: str, **kwargs: Any) -> int:
        cid = str(kwargs.get("contributing_campaign_id", ""))
        oid = (
            outpost_id
            if outpost_id in self._state.outposts
            else next(iter(self._state.outposts), "")
        )
        if not oid:
            oid = build_default_outpost(cid)["outpost_id"]
        tier = self._state.outposts[oid]["facilities"].get(facility_id, 0) + 1
        wid = _to_uuid(self._state.shared_world_id) or uuid4()
        kw = {
            **kwargs,
            "shared_world_id": wid,
            "outpost_id": oid,
            "facility_id": facility_id,
            "new_tier": tier,
            "contributing_campaign_id": _to_uuid(cid) or cid,
            "gold_spent": kwargs.get("gold_spent", 0),
            "materials_spent": kwargs.get("materials_spent") or {},
        }
        self.create_event(SharedStrongholdUpgraded, **kw)
        return tier

    def post_communal_notice(self, **kwargs: Any) -> str:
        nid = kwargs.get("notice_id") or f"notice_{uuid4().hex[:8]}"
        wid = _to_uuid(self._state.shared_world_id) or uuid4()
        cid = _to_uuid(kwargs.get("campaign_id")) or str(kwargs.get("campaign_id", ""))
        self.create_event(
            CommunalNoticePosted,
            **{**kwargs, "notice_id": nid, "shared_world_id": wid, "campaign_id": cid},
        )
        return nid


WestMarchesWorldAggregate = WestMarchesAtlasAggregate

__all__ = [
    "FACILITY_BOONS",
    "WestMarchesAtlasAggregate",
    "WestMarchesState",
    "WestMarchesWorldAggregate",
    "calculate_boons",
]
