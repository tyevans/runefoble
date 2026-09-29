"""Data loaders, aggregate resolvers, and persistence for settlement havens.

Governed by ADR-0001, ADR-0003, ADR-0007, ADR-0013, and PRD-0024.
"""

from __future__ import annotations

import contextlib
from typing import Any
from uuid import UUID

from fastapi import HTTPException
from game_session.dependencies import (
    STREAM_WEST_MARCHES,
    get_establishment_repository,
    get_settlement_establishments_index,
    get_settlement_repository,
    get_spicedb_client,
)
from game_session.settlement.auth import (
    check_establishment_read_permission,
    check_establishment_write_permission,
    check_settlement_read_permission,
    check_settlement_write_permission,
)
from game_session.settlement.establishment_aggregate import EstablishmentAggregate
from game_session.settlement.models import (
    EstablishmentState,
    SettlementProjectionResponse,
)
from game_session.settlement.settlement_aggregate import SettlementAggregate


def to_uuid(val: Any) -> UUID:
    """Convert value to UUID or raise 400 Bad Request."""
    try:
        return val if isinstance(val, UUID) else UUID(str(val))
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Invalid UUID: {val}") from e


async def save_and_publish(repo: Any, bus: Any, agg: Any) -> None:
    """Save aggregate uncommitted events and publish to West Marches stream."""
    events = list(agg.uncommitted_events)
    await repo.save(agg)
    if bus:
        for ev in events:
            with contextlib.suppress(Exception):
                await bus.publish_event(STREAM_WEST_MARCHES, ev)


async def load_settlement(sid: str, perm: str, uid: str | None) -> SettlementAggregate:
    """Load settlement aggregate and verify SpiceDB Zanzibar permissions."""
    repo = get_settlement_repository()
    try:
        agg = await repo.load(to_uuid(sid))
    except Exception as e:
        raise HTTPException(status_code=404, detail=f"Settlement '{sid}' not found") from e
    if not agg.state.is_founded:
        raise HTTPException(status_code=404, detail=f"Settlement '{sid}' not found")
    spicedb = get_spicedb_client()
    if perm == "view":
        await check_settlement_read_permission(spicedb, sid, uid)
    else:
        await check_settlement_write_permission(spicedb, sid, uid)
    return agg


async def load_establishment(eid: str, perm: str, uid: str | None) -> EstablishmentAggregate:
    """Load establishment aggregate and verify SpiceDB Zanzibar permissions."""
    repo = get_establishment_repository()
    try:
        agg = await repo.load(to_uuid(eid))
    except Exception as e:
        raise HTTPException(status_code=404, detail=f"Establishment '{eid}' not found") from e
    if not agg.state.is_constructed:
        raise HTTPException(status_code=404, detail=f"Establishment '{eid}' not found")
    spicedb = get_spicedb_client()
    if perm == "view":
        await check_establishment_read_permission(spicedb, eid, uid)
    else:
        await check_establishment_write_permission(spicedb, eid, uid)
    return agg


async def build_settlement_projection(agg: SettlementAggregate) -> SettlementProjectionResponse:
    """Build consolidated read projection including active establishments."""
    sid = str(agg.state.settlement_id or agg.aggregate_id)
    est_ids = get_settlement_establishments_index().get(sid, [])
    est_repo = get_establishment_repository()
    establishments: list[EstablishmentState] = []
    for eid in est_ids:
        try:
            e_agg = await est_repo.load(to_uuid(eid))
            if e_agg.state.is_constructed:
                establishments.append(e_agg.state)
        except Exception:
            continue

    return SettlementProjectionResponse(
        settlement_id=sid,
        campaign_id=agg.state.campaign_id,
        shared_world_id=agg.state.shared_world_id,
        name=agg.state.name,
        scale=agg.state.scale,
        tier=agg.state.tier,
        biome=agg.state.biome,
        coordinates=agg.state.coordinates,
        prosperity=agg.state.prosperity,
        max_districts=agg.state.max_districts,
        districts=agg.state.districts,
        defense_rating=agg.state.defense_rating,
        facilities=agg.state.facilities,
        active_boons=agg.state.active_boons,
        establishments=establishments,
    )


__all__ = [
    "build_settlement_projection",
    "load_establishment",
    "load_settlement",
    "save_and_publish",
    "to_uuid",
]
