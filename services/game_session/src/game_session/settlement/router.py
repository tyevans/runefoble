"""FastAPI APIRouter for settlement haven builder and establishment aggregates.

Governed by ADR-0001, ADR-0002, ADR-0007, ADR-0011, and PRD-0024.
"""

from __future__ import annotations

import contextlib
from typing import Any
from uuid import UUID, uuid4

from fastapi import APIRouter, Header, HTTPException
from game_session.dependencies import (
    STREAM_WEST_MARCHES,
    get_campaign_settlements_index,
    get_establishment_repository,
    get_event_bus,
    get_settlement_establishments_index,
    get_settlement_repository,
    get_spicedb_client,
)
from game_session.settlement.auth import (
    check_campaign_write_permission,
    check_establishment_read_permission,
    check_establishment_write_permission,
    check_settlement_read_permission,
    check_settlement_write_permission,
    write_establishment_relationships,
    write_settlement_relationships,
)
from game_session.settlement.bulletin_router import (
    decrypt_cipher_notice,
    list_bulletin_notices,
    pin_bulletin_notice,
    remove_bulletin_notice,
)
from game_session.settlement.bulletin_router import (
    router as bulletin_router,
)
from game_session.settlement.establishment_aggregate import EstablishmentAggregate
from game_session.settlement.models import (
    ConstructEstablishmentRequest,
    EstablishmentState,
    FoundSettlementRequest,
    SettlementProjectionResponse,
    UpgradeEstablishmentRequest,
    UpgradeSettlementTierRequest,
)
from game_session.settlement.settlement_aggregate import SettlementAggregate

router = APIRouter(tags=["settlement-haven-builder"])
router.include_router(bulletin_router)


def _to_uuid(val: Any) -> UUID:
    try:
        return val if isinstance(val, UUID) else UUID(str(val))
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Invalid UUID: {val}") from e


async def _save_and_publish(repo: Any, bus: Any, agg: Any) -> None:
    events = list(agg.uncommitted_events)
    await repo.save(agg)
    if bus:
        for ev in events:
            with contextlib.suppress(Exception):
                await bus.publish_event(STREAM_WEST_MARCHES, ev)


async def _load_settlement(sid: str, perm: str, uid: str | None) -> SettlementAggregate:
    repo = get_settlement_repository()
    try:
        agg = await repo.load(_to_uuid(sid))
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


async def _load_establishment(eid: str, perm: str, uid: str | None) -> EstablishmentAggregate:
    repo = get_establishment_repository()
    try:
        agg = await repo.load(_to_uuid(eid))
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


async def _build_settlement_projection(agg: SettlementAggregate) -> SettlementProjectionResponse:
    sid = str(agg.state.settlement_id or agg.aggregate_id)
    est_ids = get_settlement_establishments_index().get(sid, [])
    est_repo = get_establishment_repository()
    establishments: list[EstablishmentState] = []
    for eid in est_ids:
        try:
            e_agg = await est_repo.load(_to_uuid(eid))
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


@router.post("/api/v1/campaigns/{campaign_id}/settlements", status_code=201)
@router.post("/campaigns/{campaign_id}/settlements", status_code=201)
async def found_settlement(
    campaign_id: str,
    req: FoundSettlementRequest,
    x_user_id: str | None = Header(default=None),
) -> SettlementProjectionResponse:
    """Found a new settlement haven with scale, biome, and layout zoning."""
    spicedb, repo, bus = get_spicedb_client(), get_settlement_repository(), get_event_bus()
    await check_campaign_write_permission(spicedb, campaign_id, x_user_id)

    sid = uuid4()
    agg = SettlementAggregate(sid)
    try:
        agg.found(
            name=req.name,
            campaign_id=campaign_id,
            scale=req.scale,
            biome=req.biome,
            coordinates=req.coordinates,
            prosperity=req.prosperity,
            districts=req.districts,
            founded_by=x_user_id or "system",
            metadata=req.metadata,
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e)) from e

    await _save_and_publish(repo, bus, agg)
    await write_settlement_relationships(
        spicedb,
        settlement_id=str(sid),
        campaign_id=campaign_id,
        founder_id=x_user_id,
    )

    get_campaign_settlements_index().setdefault(campaign_id, []).append(str(sid))
    return await _build_settlement_projection(agg)


@router.get("/api/v1/campaigns/{campaign_id}/settlements/{settlement_id}")
@router.get("/campaigns/{campaign_id}/settlements/{settlement_id}")
async def get_campaign_settlement_projection(
    campaign_id: str,
    settlement_id: str,
    x_user_id: str | None = Header(default=None),
) -> SettlementProjectionResponse:
    """Query settlement projection including scale, districts, and establishments."""
    agg = await _load_settlement(settlement_id, "view", x_user_id)
    if agg.state.campaign_id and agg.state.campaign_id != campaign_id:
        raise HTTPException(
            status_code=404, detail="Settlement does not belong to specified campaign"
        )
    return await _build_settlement_projection(agg)


@router.get("/api/v1/campaigns/{campaign_id}/settlements")
@router.get("/campaigns/{campaign_id}/settlements")
async def list_campaign_settlements(
    campaign_id: str,
    x_user_id: str | None = Header(default=None),
) -> list[SettlementProjectionResponse]:
    """List all settlement projections founded for a campaign."""
    sids = get_campaign_settlements_index().get(campaign_id, [])
    results: list[SettlementProjectionResponse] = []
    repo = get_settlement_repository()
    for sid in sids:
        try:
            agg = await repo.load(_to_uuid(sid))
            if agg.state.is_founded:
                results.append(await _build_settlement_projection(agg))
        except Exception:
            continue
    return results


@router.post("/api/v1/settlements/{settlement_id}/establishments", status_code=201)
@router.post("/settlements/{settlement_id}/establishments", status_code=201)
async def construct_establishment(
    settlement_id: str,
    req: ConstructEstablishmentRequest,
    x_user_id: str | None = Header(default=None),
) -> EstablishmentState:
    """Construct a commercial, civic, or hospitality establishment within a district."""
    settlement = await _load_settlement(settlement_id, "upgrade", x_user_id)
    if req.district_id not in settlement.state.districts:
        raise HTTPException(
            status_code=400,
            detail=(
                f"District '{req.district_id}' is not zoned or unlocked in settlement '{settlement_id}'. "
                f"Available districts: {settlement.state.districts}"
            ),
        )

    spicedb = get_spicedb_client()
    est_repo = get_establishment_repository()
    bus = get_event_bus()

    eid = uuid4()
    est_agg = EstablishmentAggregate(eid)
    try:
        est_agg.construct(
            settlement_id=settlement_id,
            district_id=req.district_id,
            category=req.category,
            name=req.name,
            campaign_id=settlement.state.campaign_id,
            tier=req.tier,
            capacity=req.capacity,
            operating_cost=req.operating_cost,
            amenities=req.amenities,
            owner_id=x_user_id or "system",
            metadata=req.metadata,
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e)) from e

    await _save_and_publish(est_repo, bus, est_agg)
    await write_establishment_relationships(
        spicedb,
        establishment_id=str(eid),
        settlement_id=settlement_id,
        campaign_id=settlement.state.campaign_id,
        owner_id=x_user_id,
    )

    get_settlement_establishments_index().setdefault(settlement_id, []).append(str(eid))
    return est_agg.state


@router.post("/api/v1/settlements/{settlement_id}/upgrade-tier")
@router.post("/settlements/{settlement_id}/upgrade-tier")
async def upgrade_settlement_tier(
    settlement_id: str,
    req: UpgradeSettlementTierRequest,
    x_user_id: str | None = Header(default=None),
) -> SettlementProjectionResponse:
    """Upgrade settlement to higher civic tier."""
    agg = await _load_settlement(settlement_id, "upgrade", x_user_id)
    try:
        agg.upgrade_tier(
            new_tier=req.new_tier,
            target_scale=req.target_scale,
            prosperity=req.prosperity,
            metadata=req.metadata,
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e)) from e

    await _save_and_publish(get_settlement_repository(), get_event_bus(), agg)
    return await _build_settlement_projection(agg)


@router.get("/api/v1/settlements/{settlement_id}/establishments")
@router.get("/settlements/{settlement_id}/establishments")
async def list_settlement_establishments(
    settlement_id: str,
    x_user_id: str | None = Header(default=None),
) -> list[EstablishmentState]:
    """List all establishments located in a settlement."""
    await _load_settlement(settlement_id, "view", x_user_id)
    est_ids = get_settlement_establishments_index().get(settlement_id, [])
    est_repo = get_establishment_repository()
    results: list[EstablishmentState] = []
    for eid in est_ids:
        try:
            agg = await est_repo.load(_to_uuid(eid))
            if agg.state.is_constructed:
                results.append(agg.state)
        except Exception:
            continue
    return results


@router.get("/api/v1/establishments/{establishment_id}")
@router.get("/establishments/{establishment_id}")
async def get_establishment(
    establishment_id: str,
    x_user_id: str | None = Header(default=None),
) -> EstablishmentState:
    """Retrieve establishment details and operational stats."""
    agg = await _load_establishment(establishment_id, "view", x_user_id)
    return agg.state


@router.post("/api/v1/establishments/{establishment_id}/upgrade")
@router.post("/establishments/{establishment_id}/upgrade")
async def upgrade_establishment(
    establishment_id: str,
    req: UpgradeEstablishmentRequest,
    x_user_id: str | None = Header(default=None),
) -> EstablishmentState:
    """Upgrade establishment tier, amenities, or capacity."""
    agg = await _load_establishment(establishment_id, "manage", x_user_id)
    try:
        agg.upgrade(
            new_tier=req.tier,
            added_amenities=req.added_amenities,
            capacity=req.capacity,
            operating_cost=req.operating_cost,
            metadata=req.metadata,
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e)) from e

    await _save_and_publish(get_establishment_repository(), get_event_bus(), agg)
    return agg.state


__all__ = [
    "bulletin_router",
    "decrypt_cipher_notice",
    "list_bulletin_notices",
    "pin_bulletin_notice",
    "remove_bulletin_notice",
    "router",
]
