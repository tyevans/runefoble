"""Data loaders and aggregate resolvers for settlement havens.

Governed by ADR-0001, ADR-0003, ADR-0007, ADR-0013, and PRD-0024.
"""

from __future__ import annotations

from fastapi import HTTPException
from game_session.settlement.auth import (
    check_establishment_read_permission,
    check_establishment_write_permission,
    check_settlement_read_permission,
    check_settlement_write_permission,
)
from game_session.settlement.child_indexes import (
    ChildIndexRepository,
    list_establishments_for_settlement,
)
from game_session.settlement.establishment_aggregate import EstablishmentAggregate
from game_session.settlement.models import (
    EstablishmentState,
    SettlementProjectionResponse,
)
from game_session.settlement.repositories import SettlementRepositories
from game_session.settlement.settlement_aggregate import SettlementAggregate
from runefoble_auth.factory import get_spicedb_client
from runefoble_platform.aggregate_loading import load_if_exists
from runefoble_platform.identifiers import parse_uuid


async def load_settlement(
    repos: SettlementRepositories, sid: str, perm: str, uid: str | None
) -> SettlementAggregate:
    """Load settlement aggregate and verify SpiceDB Zanzibar permissions."""
    repo = repos.settlements
    try:
        agg = await repo.load(parse_uuid(sid, field="settlement_id"))
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


async def load_establishment(
    repos: SettlementRepositories, eid: str, perm: str, uid: str | None
) -> EstablishmentAggregate:
    """Load establishment aggregate and verify SpiceDB Zanzibar permissions."""
    repo = repos.establishments
    try:
        agg = await repo.load(parse_uuid(eid, field="establishment_id"))
    except Exception as e:
        raise HTTPException(status_code=404, detail=f"Establishment '{eid}' not found") from e
    if not agg.state.is_constructed:
        raise HTTPException(status_code=404, detail=f"Establishment '{eid}' not found")
    spicedb = get_spicedb_client()
    if perm == "view":
        await check_establishment_read_permission(spicedb, eid, uid)
    else:
        await check_establishment_write_permission(spicedb, eid, uid, perm)
    return agg


async def build_settlement_projection(
    repos: SettlementRepositories, child_indexes: ChildIndexRepository, agg: SettlementAggregate
) -> SettlementProjectionResponse:
    """Build consolidated read projection including active establishments."""
    sid = str(agg.state.settlement_id or agg.aggregate_id)
    est_ids = await list_establishments_for_settlement(child_indexes, sid)
    est_repo = repos.establishments
    establishments: list[EstablishmentState] = []
    for eid in est_ids:
        e_agg = await load_if_exists(est_repo, parse_uuid(eid, field="establishment_id"))
        if e_agg is not None and e_agg.state.is_constructed:
            establishments.append(e_agg.state)

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
]
