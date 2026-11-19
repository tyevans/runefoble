"""FastAPI APIRouter for workplace shelf inventory, restock, and vault access.

Governed by ADR-0003, ADR-0007, ADR-0013, and PRD-0024.
"""

from __future__ import annotations

from typing import Any, Literal

from fastapi import APIRouter, Depends, HTTPException
from game_session.dependencies import get_event_bus, get_worker_repository
from game_session.settlement.worker_models import WorkerInventoryItem
from game_session.settlement.workers.loaders import load_worker
from game_session.shared.identity import CallerId, get_principal
from game_session.shared.streams import STREAM_WEST_MARCHES
from runefoble_platform.event_publish import publish_aggregate_events

router = APIRouter(dependencies=[Depends(get_principal)], tags=["settlement-npc-inventory"])


@router.get("/api/v1/npcs/{npc_id}/inventory")
async def get_worker_inventory(npc_id: str, caller_id: CallerId) -> dict[str, Any]:
    """Retrieve storefront shelf stock and accessible workplace inventory."""
    agg = await load_worker(npc_id, "view", caller_id)
    return {
        "npc_id": npc_id,
        "shelf_inventory": agg.state.shelf_inventory,
        "total_shelf_items": len(agg.state.shelf_inventory),
    }


@router.get("/api/v1/npcs/{npc_id}/inventory/vault")
async def get_worker_vault(npc_id: str, caller_id: CallerId) -> list[WorkerInventoryItem]:
    """Retrieve backroom vault inventory requiring manager authorization."""
    agg = await load_worker(npc_id, "manage", caller_id)
    return agg.state.backroom_inventory


@router.get("/api/v1/npcs/{npc_id}/inventory/{item_id}")
async def get_inventory_item(npc_id: str, item_id: str, caller_id: CallerId) -> WorkerInventoryItem:
    """Lookup specific workplace shelf item pricing, stock count, and contraband status."""
    agg = await load_worker(npc_id, "view", caller_id)
    all_items = agg.state.shelf_inventory + agg.state.backroom_inventory
    item = next((i for i in all_items if i.item_id == item_id), None)
    if not item:
        raise HTTPException(
            status_code=404, detail=f"Item '{item_id}' not found in worker inventory"
        )
    return item


@router.post("/api/v1/npcs/{npc_id}/inventory/restock")
async def restock_worker_inventory(
    caller_id: CallerId,
    npc_id: str,
    item: WorkerInventoryItem,
    destination: Literal["shelf", "backroom"] = "shelf",
) -> WorkerInventoryItem:
    """Restock or add merchandise items to an NPC worker's shelf or backroom vault."""
    agg = await load_worker(npc_id, "manage", caller_id)
    result = agg.restock(item, destination)
    events = list(agg.uncommitted_events)
    await get_worker_repository().save(agg)
    if bus := get_event_bus():
        await publish_aggregate_events(bus, STREAM_WEST_MARCHES, events)
    return result
