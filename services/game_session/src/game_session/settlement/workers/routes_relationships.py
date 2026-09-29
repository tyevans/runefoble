"""FastAPI APIRouter for NPC worker relationships, mood/loyalty, and workplace rumors.

Governed by ADR-0003, ADR-0007, ADR-0013, and PRD-0024.
"""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Header
from game_session.dependencies import get_event_bus, get_worker_repository
from game_session.settlement.worker_models import (
    FormRelationshipRequest,
    NPCWorkerState,
    UpdateWorkerMoodRequest,
    WorkerRelationship,
)
from game_session.settlement.workers.loaders import load_worker, save_and_publish
from game_session.settlement.workers.operations import sync_establishment_operations

router = APIRouter(tags=["settlement-npc-relationships"])


@router.patch("/api/v1/npcs/{npc_id}/mood")
@router.patch("/npcs/{npc_id}/mood")
async def update_worker_mood(
    npc_id: str,
    req: UpdateWorkerMoodRequest,
    x_user_id: str | None = Header(default=None),
) -> NPCWorkerState:
    """Update an NPC worker's temperament, mood, and patience."""
    agg = await load_worker(npc_id, "edit_mood", x_user_id)
    agg.update_mood(req.mood, req.temperament, req.patience_delta, req.metadata)
    await save_and_publish(get_worker_repository(), get_event_bus(), agg)
    if agg.state.establishment_id:
        await sync_establishment_operations(agg.state.establishment_id)
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
    agg = await load_worker(npc_id, "manage", x_user_id)
    target = req.target_npc_id or req.target_npc or ""
    relation = req.relation_type or req.relation or "ally"

    agg.form_relationship(target, relation, req.intensity, req.notes, req.metadata)
    await save_and_publish(get_worker_repository(), get_event_bus(), agg)
    if agg.state.establishment_id:
        await sync_establishment_operations(agg.state.establishment_id)
    agg.refresh_computed_fields()
    return agg.state


@router.get("/api/v1/npcs/{npc_id}/relationships")
@router.get("/npcs/{npc_id}/relationships")
async def get_npc_relationships(
    npc_id: str, x_user_id: str | None = Header(default=None)
) -> list[WorkerRelationship]:
    """Query interpersonal ties and social graph connections for an NPC worker."""
    agg = await load_worker(npc_id, "view", x_user_id)
    return agg.state.relationships


@router.get("/api/v1/npcs/{npc_id}/rumors")
@router.get("/npcs/{npc_id}/rumors")
async def get_worker_rumors(
    npc_id: str, x_user_id: str | None = Header(default=None)
) -> list[dict[str, Any]]:
    """Discover workplace rumors, secrets, and grievances overheard by this NPC worker."""
    agg = await load_worker(npc_id, "view", x_user_id)
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
