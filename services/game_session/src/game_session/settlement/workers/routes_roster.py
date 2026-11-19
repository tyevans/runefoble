"""FastAPI APIRouter for establishment worker roster and staff assignment.

Governed by ADR-0003, ADR-0007, ADR-0013, and PRD-0024.
"""

from __future__ import annotations

from fastapi import APIRouter, Depends
from game_session.settlement.child_indexes import list_workers_for_establishment
from game_session.settlement.repositories import SettlementRepos
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
)
from game_session.settlement.workers.operations import (
    create_and_assign_worker,
    sync_establishment_operations,
)
from game_session.shared.child_index_queries import ChildIndexes
from game_session.shared.container_access import EventBus
from game_session.shared.identity import CallerId, get_principal
from game_session.shared.streams import STREAM_WEST_MARCHES
from runefoble_platform.aggregate_loading import load_if_exists
from runefoble_platform.event_publish import publish_aggregate_events
from runefoble_platform.identifiers import parse_uuid

router = APIRouter(dependencies=[Depends(get_principal)], tags=["settlement-npc-workers"])


@router.post("/api/v1/establishments/{establishment_id}/workers", status_code=201)
async def assign_worker(
    establishment_id: str,
    req: AssignWorkerRequest,
    caller_id: CallerId,
    repos: SettlementRepos,
    events: EventBus,
    child_indexes: ChildIndexes,
) -> NPCWorkerState:
    """Assign an NPC worker to a role in an establishment storefront."""
    est = await load_establishment(repos, establishment_id, "manage", caller_id)
    return await create_and_assign_worker(
        repos, child_indexes, events, establishment_id, est, req, caller_id
    )


@router.get("/api/v1/establishments/{establishment_id}/workers")
async def list_establishment_workers(
    establishment_id: str,
    caller_id: CallerId,
    repos: SettlementRepos,
    child_indexes: ChildIndexes,
) -> list[NPCWorkerState]:
    """Query active staff assigned to an establishment with inventories and ties."""
    est = await load_establishment(repos, establishment_id, "view", caller_id)
    worker_ids = await list_workers_for_establishment(child_indexes, establishment_id)
    worker_repo = repos.workers

    workers: list[NPCWorkerState] = []
    for wid in worker_ids:
        w_agg = await load_if_exists(worker_repo, parse_uuid(wid, field="worker_id"))
        if w_agg is not None and w_agg.state.status == "active":
            workers.append(w_agg.state)

    for w in workers:
        w.interpersonal_tension = compute_worker_tension(w, workers)
        w.service_quality_contribution = calculate_service_quality_contribution(w, est.state.tier)
        w.redstring_edges = serialize_to_redstring_edges(w)
    return workers


@router.get("/api/v1/establishments/{establishment_id}/roster")
async def get_establishment_roster(
    establishment_id: str,
    caller_id: CallerId,
    repos: SettlementRepos,
    events: EventBus,
    child_indexes: ChildIndexes,
) -> EstablishmentRosterResponse:
    """Query comprehensive establishment roster with operations projection and graph edges."""
    workers = await list_establishment_workers(establishment_id, caller_id, repos, child_indexes)
    ops = await sync_establishment_operations(repos, child_indexes, events, establishment_id)
    return EstablishmentRosterResponse(
        establishment_id=establishment_id,
        workers=workers,
        operations=ops,
        projected_service_quality=ops.projected_service_quality,
        service_quality_tier=ops.service_quality_tier,
        social_graph_edges=[e for w in workers for e in w.redstring_edges],
    )


@router.post("/api/v1/establishments/{establishment_id}/workers/{npc_id}/relieve")
async def relieve_worker(
    caller_id: CallerId,
    establishment_id: str,
    npc_id: str,
    req: RelieveWorkerRequest,
    repos: SettlementRepos,
    events: EventBus,
    child_indexes: ChildIndexes,
) -> NPCWorkerState:
    """Relieve an NPC worker from an establishment duty."""
    await load_establishment(repos, establishment_id, "manage", caller_id)
    agg = await load_worker(repos, npc_id, "manage", caller_id)
    agg.relieve(establishment_id=establishment_id, reason=req.reason)
    new_events = list(agg.uncommitted_events)
    await repos.workers.save(agg)
    await sync_establishment_operations(repos, child_indexes, events, establishment_id)
    if bus := events.get():
        await publish_aggregate_events(bus, STREAM_WEST_MARCHES, new_events)
    return agg.state


@router.get("/api/v1/npcs/{npc_id}")
async def get_worker(npc_id: str, caller_id: CallerId, repos: SettlementRepos) -> NPCWorkerState:
    """Retrieve an NPC worker profile, traits, inventories, and social ties."""
    agg = await load_worker(repos, npc_id, "view", caller_id)
    agg.refresh_computed_fields()
    return agg.state
