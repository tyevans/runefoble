"""Modular settlement workers subpackage providing aggregates and sub-routers.

Governed by ADR-0003, ADR-0007, ADR-0013, and PRD-0024.
"""

from __future__ import annotations

from typing import Any

from game_session.settlement.worker_aggregate import (
    AssignWorkerRequest,
    BigFivePersonality,
    EstablishmentOperationsSummary,
    EstablishmentRosterResponse,
    FormRelationshipRequest,
    NPCWorkerAggregate,
    NPCWorkerState,
    RelieveWorkerRequest,
    UpdateWorkerMoodRequest,
    WorkerInventoryItem,
    WorkerRelationship,
)

__all__ = [
    "AssignWorkerRequest",
    "BigFivePersonality",
    "EstablishmentOperationsSummary",
    "EstablishmentRosterResponse",
    "FormRelationshipRequest",
    "NPCWorkerAggregate",
    "NPCWorkerState",
    "RelieveWorkerRequest",
    "UpdateWorkerMoodRequest",
    "WorkerInventoryItem",
    "WorkerRelationship",
    "inventory_router",
    "relationships_router",
    "roster_router",
]


def __getattr__(name: str) -> Any:
    if name == "inventory_router":
        from game_session.settlement.workers.routes_inventory import router

        return router
    if name == "relationships_router":
        from game_session.settlement.workers.routes_relationships import router

        return router
    if name == "roster_router":
        from game_session.settlement.workers.routes_roster import router

        return router
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
