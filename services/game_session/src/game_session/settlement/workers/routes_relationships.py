"""FastAPI APIRouter for NPC worker relationships, mood/loyalty, and workplace rumors.

Governed by ADR-0003, ADR-0007, ADR-0013, and PRD-0024.
"""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Depends
from game_session.dependencies import get_event_bus, get_worker_repository
from game_session.settlement.worker_models import (
    FormRelationshipRequest,
    NPCWorkerState,
    UpdateWorkerMoodRequest,
    WorkerRelationship,
)
from game_session.settlement.workers.loaders import load_worker
from game_session.settlement.workers.operations import sync_establishment_operations
from game_session.shared.identity import CallerId, get_principal
from game_session.shared.streams import STREAM_WEST_MARCHES
from runefoble_platform.event_publish import publish_aggregate_events

router = APIRouter(dependencies=[Depends(get_principal)], tags=["settlement-npc-relationships"])


@router.patch("/api/v1/npcs/{npc_id}/mood")
async def update_worker_mood(
    caller_id: CallerId,
    npc_id: str,
    req: UpdateWorkerMoodRequest,
) -> NPCWorkerState:
    """Update an NPC worker's temperament, mood, and patience."""
    agg = await load_worker(npc_id, "edit_mood", caller_id)
    agg.update_mood(req.mood, req.temperament, req.patience_delta, req.metadata)
    events = list(agg.uncommitted_events)
    await get_worker_repository().save(agg)
    if agg.state.establishment_id:
        await sync_establishment_operations(agg.state.establishment_id)
    if bus := get_event_bus():
        await publish_aggregate_events(bus, STREAM_WEST_MARCHES, events)
    agg.refresh_computed_fields()
    return agg.state


@router.post("/api/v1/npcs/{npc_id}/relationships", status_code=201)
async def form_npc_relationship(
    caller_id: CallerId,
    npc_id: str,
    req: FormRelationshipRequest,
) -> NPCWorkerState:
    """Record an interpersonal social or supply tie between two NPCs."""
    agg = await load_worker(npc_id, "manage", caller_id)
    agg.form_relationship(
        req.target_npc_id, req.relation_type, req.intensity, req.notes, req.metadata
    )
    events = list(agg.uncommitted_events)
    await get_worker_repository().save(agg)
    if agg.state.establishment_id:
        await sync_establishment_operations(agg.state.establishment_id)
    if bus := get_event_bus():
        await publish_aggregate_events(bus, STREAM_WEST_MARCHES, events)
    agg.refresh_computed_fields()
    return agg.state


@router.get("/api/v1/npcs/{npc_id}/relationships")
async def get_npc_relationships(npc_id: str, caller_id: CallerId) -> list[WorkerRelationship]:
    """Query interpersonal ties and social graph connections for an NPC worker."""
    agg = await load_worker(npc_id, "view", caller_id)
    return agg.state.relationships


@router.get("/api/v1/npcs/{npc_id}/rumors")
async def get_worker_rumors(npc_id: str, caller_id: CallerId) -> list[dict[str, Any]]:
    """Discover workplace rumors, secrets, and grievances overheard by this NPC worker."""
    agg = await load_worker(npc_id, "view", caller_id)
    rumors: list[dict[str, Any]] = [
        {"topic": r.relation_type, "detail": r.notes, "source": r.target_npc_id}
        for r in agg.state.relationships
        if r.notes
    ]
    if "grievance" in agg.state.metadata:
        rumors.append(
            {
                "topic": "grievance",
                "detail": str(agg.state.metadata["grievance"]),
                "source": agg.state.name,
            }
        )
    return rumors
