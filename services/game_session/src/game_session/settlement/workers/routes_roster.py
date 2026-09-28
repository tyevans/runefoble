"""FastAPI APIRouter for establishment worker roster and staff assignment.

Governed by ADR-0003, ADR-0007, ADR-0013, and PRD-0024.
"""

from __future__ import annotations

import contextlib

from fastapi import APIRouter, Header
from game_session.dependencies import (
    get_establishment_workers_index,
    get_event_bus,
    get_worker_repository,
)
from game_session.settlement.worker_graph import (
    calculate_service_quality_contribution,
    compute_worker_tension,
    serialize_to_redstring_edges,
)
from game_session.settlement.worker_models import (
    AssignWorkerRequest,
    EstablishmentRosterResponse,
    NPCWorkerState,
    RelieveWorkerRequest,
)
from game_session.settlement.workers.loaders import (
    load_establishment,
    load_worker,
    save_and_publish,
    to_uuid,
)
from game_session.settlement.workers.operations import (
    create_and_assign_worker,
    sync_establishment_operations,
)

router = APIRouter(tags=["settlement-npc-workers"])


@router.post("/api/v1/establishments/{establishment_id}/workers", status_code=201)
@router.post("/establishments/{establishment_id}/workers", status_code=201)
async def assign_worker(
    establishment_id: str, req: AssignWorkerRequest, x_user_id: str | None = Header(default=None)
) -> NPCWorkerState:
    """Assign an NPC worker to a role in an establishment storefront."""
    est = await load_establishment(establishment_id, "manage", x_user_id)
    return await create_and_assign_worker(establishment_id, est, req, x_user_id)


@router.get("/api/v1/establishments/{establishment_id}/workers")
@router.get("/establishments/{establishment_id}/workers")
async def list_establishment_workers(
    establishment_id: str, x_user_id: str | None = Header(default=None)
) -> list[NPCWorkerState]:
    """Query active staff assigned to an establishment with inventories and ties."""
    est = await load_establishment(establishment_id, "view", x_user_id)
    worker_ids = get_establishment_workers_index().get(establishment_id, [])
    worker_repo = get_worker_repository()

    workers: list[NPCWorkerState] = []
    for wid in worker_ids:
        with contextlib.suppress(Exception):
            w_agg = await worker_repo.load(to_uuid(wid))
            if w_agg.state.status == "active":
                workers.append(w_agg.state)

    for w in workers:
        w.interpersonal_tension = compute_worker_tension(w, workers)
        w.service_quality_contribution = calculate_service_quality_contribution(w, est.state.tier)
        w.redstring_edges = serialize_to_redstring_edges(w)
    return workers


@router.get("/api/v1/establishments/{establishment_id}/roster")
@router.get("/establishments/{establishment_id}/roster")
async def get_establishment_roster(
    establishment_id: str, x_user_id: str | None = Header(default=None)
) -> EstablishmentRosterResponse:
    """Query comprehensive establishment roster with operations projection and graph edges."""
    workers = await list_establishment_workers(establishment_id, x_user_id)
    ops = await sync_establishment_operations(establishment_id)
    return EstablishmentRosterResponse(
        establishment_id=establishment_id,
        workers=workers,
        operations=ops,
        projected_service_quality=ops.projected_service_quality,
        service_quality_tier=ops.service_quality_tier,
        social_graph_edges=[e for w in workers for e in w.redstring_edges],
    )


@router.post("/api/v1/establishments/{establishment_id}/workers/{npc_id}/relieve")
@router.post("/establishments/{establishment_id}/workers/{npc_id}/relieve")
async def relieve_worker(
    establishment_id: str,
    npc_id: str,
    req: RelieveWorkerRequest,
    x_user_id: str | None = Header(default=None),
) -> NPCWorkerState:
    """Relieve an NPC worker from an establishment duty."""
    await load_establishment(establishment_id, "manage", x_user_id)
    agg = await load_worker(npc_id, "manage", x_user_id)
    agg.relieve(establishment_id=establishment_id, reason=req.reason)
    await save_and_publish(get_worker_repository(), get_event_bus(), agg)
    await sync_establishment_operations(establishment_id)
    return agg.state


@router.get("/api/v1/npcs/{npc_id}")
@router.get("/npcs/{npc_id}")
async def get_worker(npc_id: str, x_user_id: str | None = Header(default=None)) -> NPCWorkerState:
    """Retrieve an NPC worker profile, traits, inventories, and social ties."""
    agg = await load_worker(npc_id, "view", x_user_id)
    agg.refresh_computed_fields()
    return agg.state
