"""FastAPI APIRouter for assignable NPC worker engine and social relationship graph.

Governed by ADR-0001, ADR-0002, ADR-0007, ADR-0011, and PRD-0024.
"""

from __future__ import annotations

import contextlib
from typing import Any
from uuid import UUID, uuid4

from fastapi import APIRouter, Header, HTTPException
from game_session.dependencies import (
    STREAM_WEST_MARCHES,
    get_establishment_repository,
    get_establishment_workers_index,
    get_event_bus,
    get_spicedb_client,
    get_worker_repository,
)
from game_session.settlement.auth import (
    check_establishment_read_permission,
    check_establishment_write_permission,
    check_npc_read_permission,
    check_npc_write_permission,
    write_npc_relationships,
)
from game_session.settlement.establishment_aggregate import EstablishmentAggregate
from game_session.settlement.worker_graph import (
    calculate_establishment_operations,
    calculate_service_quality_contribution,
    compute_worker_tension,
    serialize_to_redstring_edges,
)
from game_session.settlement.worker_models import (
    AssignWorkerRequest,
    EstablishmentOperationsSummary,
    EstablishmentRosterResponse,
    FormRelationshipRequest,
    NPCWorkerState,
    RelieveWorkerRequest,
    UpdateWorkerMoodRequest,
    WorkerInventoryItem,
    WorkerRelationship,
)
from game_session.settlement.workers import NPCWorkerAggregate

router = APIRouter(tags=["settlement-npc-workers"])


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


async def _load_worker(nid: str, perm: str, uid: str | None) -> NPCWorkerAggregate:
    repo = get_worker_repository()
    try:
        agg = await repo.load(_to_uuid(nid))
    except Exception as e:
        raise HTTPException(status_code=404, detail=f"Worker '{nid}' not found") from e
    if not agg.state.npc_id:
        raise HTTPException(status_code=404, detail=f"Worker '{nid}' not found")
    spicedb = get_spicedb_client()
    if perm == "view":
        await check_npc_read_permission(spicedb, nid, uid)
    else:
        await check_npc_write_permission(spicedb, nid, uid)
    return agg


async def _sync_establishment_operations(establishment_id: str) -> EstablishmentOperationsSummary:
    est_repo = get_establishment_repository()
    est = await est_repo.load(_to_uuid(establishment_id))
    bus = get_event_bus()

    worker_ids = get_establishment_workers_index().get(establishment_id, [])
    worker_repo = get_worker_repository()
    workers: list[NPCWorkerState] = []
    for wid in worker_ids:
        try:
            w_agg = await worker_repo.load(_to_uuid(wid))
            if w_agg.state.status == "active":
                workers.append(w_agg.state)
        except Exception:
            continue

    q_score, q_tier, wages, net_cost, tension, morale = calculate_establishment_operations(
        base_cost=est.state.operating_cost,
        establishment_tier=est.state.tier,
        workers=workers,
    )

    active_ids = [w.npc_id for w in workers]
    est.sync_operations(
        staff=active_ids,
        total_wages=wages,
        projected_service_quality=q_score,
        service_quality_tier=q_tier,
        interpersonal_tension_index=tension,
    )
    await _save_and_publish(est_repo, bus, est)

    return EstablishmentOperationsSummary(
        total_staff=len(active_ids),
        total_wages=wages,
        net_operating_cost=net_cost,
        average_morale=morale,
        interpersonal_tension_index=tension,
        projected_service_quality=q_score,
        service_quality_tier=q_tier,
    )


@router.post("/api/v1/establishments/{establishment_id}/workers", status_code=201)
@router.post("/establishments/{establishment_id}/workers", status_code=201)
async def assign_worker(
    establishment_id: str,
    req: AssignWorkerRequest,
    x_user_id: str | None = Header(default=None),
) -> NPCWorkerState:
    """Assign an NPC worker to a role in an establishment storefront."""
    est = await _load_establishment(establishment_id, "manage", x_user_id)
    spicedb, worker_repo, bus = (
        get_spicedb_client(),
        get_worker_repository(),
        get_event_bus(),
    )

    wage = req.wage_gold if req.wage_gold is not None else req.wage
    nid = req.npc_id or str(uuid4())
    agg = NPCWorkerAggregate(_to_uuid(nid))

    shelf_items = [
        i.model_dump() if isinstance(i, WorkerInventoryItem) else i for i in req.shelf_inventory
    ]
    backroom_source = (
        req.vault_inventory if req.vault_inventory is not None else req.backroom_inventory
    )
    backroom_items = [
        i.model_dump() if isinstance(i, WorkerInventoryItem) else i for i in backroom_source
    ]

    agg.assign(
        establishment_id=establishment_id,
        role=req.role,
        wage=wage,
        name=req.name,
        campaign_id=est.state.campaign_id,
        traits=req.traits,
        vices=req.vices,
        trade_proficiencies=req.trade_proficiencies,
        shelf_inventory=shelf_items,
        backroom_inventory=backroom_items,
        patience=req.patience,
        metadata={
            **req.metadata,
            "mood": req.mood,
            "temperament": req.temperament,
            "patience": req.patience,
        },
    )

    if req.mood or req.temperament:
        agg.update_mood(
            mood=req.mood,
            temperament=req.temperament,
            patience_delta=0,
        )

    for rel in req.relationships:
        r_model = WorkerRelationship.model_validate(rel)
        agg.form_relationship(
            target_npc_id=r_model.target_npc_id,
            relation_type=r_model.relation_type,
            intensity=r_model.intensity,
            notes=r_model.notes,
            metadata=r_model.metadata,
        )

    await _save_and_publish(worker_repo, bus, agg)

    w_index = get_establishment_workers_index().setdefault(establishment_id, [])
    if nid not in w_index:
        w_index.append(nid)

    await write_npc_relationships(
        spicedb,
        npc_id=nid,
        establishment_id=establishment_id,
        campaign_id=est.state.campaign_id,
        manager_id=x_user_id,
    )

    await _sync_establishment_operations(establishment_id)

    agg.refresh_computed_fields(establishment_tier=est.state.tier)
    return agg.state


@router.get("/api/v1/establishments/{establishment_id}/workers")
@router.get("/establishments/{establishment_id}/workers")
async def list_establishment_workers(
    establishment_id: str,
    x_user_id: str | None = Header(default=None),
) -> list[NPCWorkerState]:
    """Query active staff assigned to an establishment with inventories and ties."""
    est = await _load_establishment(establishment_id, "view", x_user_id)
    worker_ids = get_establishment_workers_index().get(establishment_id, [])
    worker_repo = get_worker_repository()

    workers: list[NPCWorkerState] = []
    for wid in worker_ids:
        try:
            w_agg = await worker_repo.load(_to_uuid(wid))
            if w_agg.state.status == "active":
                workers.append(w_agg.state)
        except Exception:
            continue

    for w in workers:
        w.interpersonal_tension = compute_worker_tension(w, workers)
        w.service_quality_contribution = calculate_service_quality_contribution(w, est.state.tier)
        w.redstring_edges = serialize_to_redstring_edges(w)

    return workers


@router.get("/api/v1/establishments/{establishment_id}/roster")
@router.get("/establishments/{establishment_id}/roster")
async def get_establishment_roster(
    establishment_id: str,
    x_user_id: str | None = Header(default=None),
) -> EstablishmentRosterResponse:
    """Query comprehensive establishment roster with operations projection and graph edges."""
    workers = await list_establishment_workers(establishment_id, x_user_id)
    ops = await _sync_establishment_operations(establishment_id)

    all_edges: list[dict[str, Any]] = []
    for w in workers:
        all_edges.extend(w.redstring_edges)

    return EstablishmentRosterResponse(
        establishment_id=establishment_id,
        workers=workers,
        operations=ops,
        projected_service_quality=ops.projected_service_quality,
        service_quality_tier=ops.service_quality_tier,
        social_graph_edges=all_edges,
    )


@router.post("/api/v1/establishments/{establishment_id}/workers/{npc_id}/relieve")
@router.post("/establishments/{establishment_id}/workers/{npc_id}/relieve")
async def relieve_worker(
    establishment_id: str,
    npc_id: str,
    req: RelieveWorkerRequest,
    x_user_id: str | None = Header(default=None),
) -> NPCWorkerState:
    """Relieve an NPC worker from an establishment role."""
    await _load_establishment(establishment_id, "manage", x_user_id)
    agg = await _load_worker(npc_id, "manage", x_user_id)
    agg.relieve(establishment_id=establishment_id, reason=req.reason)
    await _save_and_publish(get_worker_repository(), get_event_bus(), agg)
    await _sync_establishment_operations(establishment_id)
    return agg.state


@router.patch("/api/v1/npcs/{npc_id}/mood")
@router.patch("/npcs/{npc_id}/mood")
async def update_worker_mood(
    npc_id: str,
    req: UpdateWorkerMoodRequest,
    x_user_id: str | None = Header(default=None),
) -> NPCWorkerState:
    """Update an NPC worker's temperament, mood, and patience."""
    agg = await _load_worker(npc_id, "edit_mood", x_user_id)
    agg.update_mood(
        mood=req.mood,
        temperament=req.temperament,
        patience_delta=req.patience_delta,
        metadata=req.metadata,
    )
    await _save_and_publish(get_worker_repository(), get_event_bus(), agg)

    if agg.state.establishment_id:
        await _sync_establishment_operations(agg.state.establishment_id)

    agg.refresh_computed_fields()
    return agg.state


@router.get("/api/v1/npcs/{npc_id}")
@router.get("/npcs/{npc_id}")
async def get_worker(
    npc_id: str,
    x_user_id: str | None = Header(default=None),
) -> NPCWorkerState:
    """Retrieve an NPC worker profile, traits, inventories, and social ties."""
    agg = await _load_worker(npc_id, "view", x_user_id)
    agg.refresh_computed_fields()
    return agg.state


@router.post("/api/v1/npcs/{npc_id}/relationships", status_code=201)
@router.post("/npcs/{npc_id}/relationships", status_code=201)
async def form_npc_relationship(
    npc_id: str,
    req: FormRelationshipRequest,
    x_user_id: str | None = Header(default=None),
) -> NPCWorkerState:
    """Record an interpersonal social or supply tie between two NPCs."""
    agg = await _load_worker(npc_id, "manage", x_user_id)
    target = req.target_npc_id or req.target_npc or ""
    relation = req.relation_type or req.relation or "ally"

    agg.form_relationship(
        target_npc_id=target,
        relation_type=relation,
        intensity=req.intensity,
        notes=req.notes,
        metadata=req.metadata,
    )
    await _save_and_publish(get_worker_repository(), get_event_bus(), agg)

    if agg.state.establishment_id:
        await _sync_establishment_operations(agg.state.establishment_id)

    agg.refresh_computed_fields()
    return agg.state
