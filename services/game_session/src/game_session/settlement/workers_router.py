"""Aggregator APIRouter for settlement NPC workers, relationships, and inventories.

Governed by ADR-0003, ADR-0007, ADR-0013, and PRD-0024.
"""

from __future__ import annotations

from fastapi import APIRouter
from game_session.settlement.workers.routes_inventory import router as inventory_router
from game_session.settlement.workers.routes_relationships import (
    router as relationships_router,
)
from game_session.settlement.workers.routes_roster import router as roster_router

router = APIRouter(tags=["settlement-npc-workers"])
router.include_router(roster_router)
router.include_router(relationships_router)
router.include_router(inventory_router)

__all__ = [
    "inventory_router",
    "relationships_router",
    "roster_router",
    "router",
]
