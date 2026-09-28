"""FastAPI APIRouter for workplace shelf inventory, restock, and vault access.

Governed by ADR-0003, ADR-0007, ADR-0013, and PRD-0024.
"""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Header, HTTPException
from game_session.dependencies import get_event_bus, get_worker_repository
from game_session.settlement.worker_models import WorkerInventoryItem
from game_session.settlement.workers.loaders import load_worker, save_and_publish

router = APIRouter(tags=["settlement-npc-inventory"])


@router.get("/api/v1/npcs/{npc_id}/inventory")
@router.get("/npcs/{npc_id}/inventory")
async def get_worker_inventory(
    npc_id: str, x_user_id: str | None = Header(default=None)
) -> dict[str, Any]:
    """Retrieve storefront shelf stock and accessible workplace inventory."""
    agg = await load_worker(npc_id, "view", x_user_id)
    return {
        "npc_id": npc_id,
        "shelf_inventory": agg.state.shelf_inventory,
        "total_shelf_items": len(agg.state.shelf_inventory),
    }


@router.get("/api/v1/npcs/{npc_id}/inventory/vault")
@router.get("/npcs/{npc_id}/inventory/vault")
async def get_worker_vault(
    npc_id: str, x_user_id: str | None = Header(default=None)
) -> list[WorkerInventoryItem]:
    """Retrieve backroom vault inventory requiring manager authorization."""
    agg = await load_worker(npc_id, "manage", x_user_id)
    return agg.state.backroom_inventory


@router.get("/api/v1/npcs/{npc_id}/inventory/{item_id}")
@router.get("/npcs/{npc_id}/inventory/{item_id}")
async def get_inventory_item(
    npc_id: str, item_id: str, x_user_id: str | None = Header(default=None)
) -> WorkerInventoryItem:
    """Lookup specific workplace shelf item pricing, stock count, and contraband status."""
    agg = await load_worker(npc_id, "view", x_user_id)
    all_items = agg.state.shelf_inventory + agg.state.backroom_inventory
    item = next((i for i in all_items if i.item_id == item_id), None)
    if not item:
        raise HTTPException(
            status_code=404, detail=f"Item '{item_id}' not found in worker inventory"
        )
    return item


@router.post("/api/v1/npcs/{npc_id}/inventory/restock")
@router.post("/npcs/{npc_id}/inventory/restock")
async def restock_worker_inventory(
    npc_id: str,
    item: WorkerInventoryItem,
    destination: str = "shelf",
    x_user_id: str | None = Header(default=None),
) -> WorkerInventoryItem:
    """Restock or add merchandise items to an NPC worker's shelf or backroom vault."""
    agg = await load_worker(npc_id, "manage", x_user_id)
    target_list = (
        agg.state.shelf_inventory if destination == "shelf" else agg.state.backroom_inventory
    )
    existing = next((i for i in target_list if i.item_id == item.item_id), None)
    if existing:
        existing.quantity += item.quantity
        existing.unit_price = item.unit_price
        result = existing
    else:
        target_list.append(item)
        result = item
    await save_and_publish(get_worker_repository(), get_event_bus(), agg)
    return result
