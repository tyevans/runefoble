"""Operations syncing and assignment orchestration for NPC workers.

Governed by ADR-0003, ADR-0007, ADR-0013, and PRD-0024.
"""

from __future__ import annotations

from typing import Any
from uuid import uuid4

from game_session.child_index import ChildIndexKind
from game_session.dependencies import (
    get_establishment_repository,
    get_event_bus,
    get_worker_repository,
)
from game_session.events import STREAM_WEST_MARCHES
from game_session.queries import link_child, list_workers_for_establishment
from game_session.settlement.auth import write_npc_relationships
from game_session.settlement.establishment_aggregate import EstablishmentAggregate
from game_session.settlement.worker_aggregate import NPCWorkerAggregate
from game_session.settlement.worker_graph import calculate_establishment_operations
from game_session.settlement.worker_models import (
    AssignWorkerRequest,
    EstablishmentOperationsSummary,
    NPCWorkerState,
    WorkerInventoryItem,
    WorkerRelationship,
)
from runefoble_auth.factory import get_spicedb_client
from runefoble_platform.aggregate_loading import load_if_exists
from runefoble_platform.event_publish import publish_aggregate_events
from runefoble_platform.identifiers import parse_uuid


def _dump_items(items: list[Any]) -> list[Any]:
    return [i.model_dump() if isinstance(i, WorkerInventoryItem) else i for i in items]


async def sync_establishment_operations(establishment_id: str) -> EstablishmentOperationsSummary:
    """Recalculate establishment operating metrics and save projection."""
    est_repo = get_establishment_repository()
    est = await est_repo.load(parse_uuid(establishment_id, field="establishment_id"))
    worker_ids = await list_workers_for_establishment(establishment_id)
    worker_repo = get_worker_repository()

    workers: list[NPCWorkerState] = []
    for wid in worker_ids:
        w_agg = await load_if_exists(worker_repo, parse_uuid(wid, field="worker_id"))
        if w_agg is not None and w_agg.state.status == "active":
            workers.append(w_agg.state)

    q_score, q_tier, wages, net_cost, tension, morale = calculate_establishment_operations(
        base_cost=est.state.operating_cost, establishment_tier=est.state.tier, workers=workers
    )
    active_ids = [w.npc_id for w in workers]
    est.sync_operations(
        staff=active_ids,
        total_wages=wages,
        projected_service_quality=q_score,
        service_quality_tier=q_tier,
        interpersonal_tension_index=tension,
    )
    events = list(est.uncommitted_events)
    await est_repo.save(est)
    if bus := get_event_bus():
        await publish_aggregate_events(bus, STREAM_WEST_MARCHES, events)

    return EstablishmentOperationsSummary(
        total_staff=len(active_ids),
        total_wages=wages,
        net_operating_cost=net_cost,
        average_morale=morale,
        interpersonal_tension_index=tension,
        projected_service_quality=q_score,
        service_quality_tier=q_tier,
    )


async def create_and_assign_worker(
    establishment_id: str, est: EstablishmentAggregate, req: AssignWorkerRequest, uid: str | None
) -> NPCWorkerState:
    """Instantiate and configure new worker aggregate for establishment assignment."""
    spicedb, worker_repo = get_spicedb_client(), get_worker_repository()
    wage = req.wage_gold if req.wage_gold is not None else req.wage
    nid = req.npc_id or str(uuid4())
    agg = NPCWorkerAggregate(parse_uuid(nid, field="worker_id"))

    vault_src = req.vault_inventory if req.vault_inventory is not None else req.backroom_inventory
    meta = {
        **req.metadata,
        "mood": req.mood,
        "temperament": req.temperament,
        "patience": req.patience,
    }
    agg.assign(
        establishment_id=establishment_id,
        role=req.role,
        wage=wage,
        name=req.name,
        campaign_id=est.state.campaign_id,
        traits=req.traits,
        vices=req.vices,
        trade_proficiencies=req.trade_proficiencies,
        shelf_inventory=_dump_items(req.shelf_inventory),
        backroom_inventory=_dump_items(vault_src),
        patience=req.patience,
        metadata=meta,
    )
    if req.mood or req.temperament:
        agg.update_mood(mood=req.mood, temperament=req.temperament, patience_delta=0)
    for rel in req.relationships:
        r = WorkerRelationship.model_validate(rel)
        agg.form_relationship(r.target_npc_id, r.relation_type, r.intensity, r.notes, r.metadata)
    events = list(agg.uncommitted_events)
    await worker_repo.save(agg)

    await link_child(ChildIndexKind.ESTABLISHMENT_WORKERS, establishment_id, str(agg.aggregate_id))

    await write_npc_relationships(
        spicedb,
        npc_id=nid,
        establishment_id=establishment_id,
        campaign_id=est.state.campaign_id,
        manager_id=uid,
    )
    await sync_establishment_operations(establishment_id)
    if bus := get_event_bus():
        await publish_aggregate_events(bus, STREAM_WEST_MARCHES, events)
    agg.refresh_computed_fields(establishment_tier=est.state.tier)
    return agg.state
