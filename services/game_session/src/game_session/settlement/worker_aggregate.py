"""Event-sourced NPCWorker Aggregate managing staff roles, mood, and relationships.

Governed by ADR-0001, ADR-0002, ADR-0007, ADR-0011, and Hard Invariant 2.
"""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Any
from uuid import UUID, uuid4

from eventsource.domain.aggregate import DeclarativeAggregate
from eventsource.domain.decorators import handles
from game_session.settlement.worker_graph import (
    calculate_establishment_operations,
    calculate_service_quality_contribution,
    compute_supply_chain_dependencies,
    compute_worker_tension,
    serialize_to_redstring_edges,
)
from game_session.settlement.worker_models import (
    AssignWorkerRequest,
    BigFivePersonality,
    EstablishmentOperationsSummary,
    EstablishmentRosterResponse,
    FormRelationshipRequest,
    NPCWorkerState,
    RelieveWorkerRequest,
    UpdateWorkerMoodRequest,
    WorkerInventoryItem,
    WorkerRelationship,
)
from runefoble_events.settlement_workers import (
    NPCMoodUpdated,
    NPCRelationshipFormed,
    NPCWorkerAssigned,
    NPCWorkerRelieved,
)


def _to_uuid(val: Any) -> UUID:
    try:
        return val if isinstance(val, UUID) else UUID(str(val))
    except Exception:
        return uuid4()


class NPCWorkerAggregate(DeclarativeAggregate[NPCWorkerState]):
    """Event-sourced aggregate managing NPC worker temperament, inventories, and social ties."""

    aggregate_type = "NPCWorker"
    requires_creation_event = False

    def __init__(self, aggregate_id: Any = None, **kwargs: Any) -> None:
        super().__init__(aggregate_id=aggregate_id, **kwargs)
        if self._state is None:
            self._state = NPCWorkerState(npc_id=str(aggregate_id or ""))

    @handles(NPCWorkerAssigned)
    def handle_assigned(self, ev: NPCWorkerAssigned) -> None:
        """Handle worker assignment."""
        self._state.npc_id = ev.npc_id or str(ev.aggregate_id)
        self._state.establishment_id = ev.establishment_id
        self._state.role = ev.role
        self._state.wage = ev.wage
        self._state.assigned_at = ev.assigned_at or datetime.now(UTC).isoformat()
        self._state.status = "active"
        if ev.name:
            self._state.name = ev.name
        if ev.campaign_id:
            self._state.campaign_id = ev.campaign_id
        if ev.traits:
            self._state.traits = BigFivePersonality.model_validate(ev.traits)
        if ev.vices:
            self._state.vices = list(ev.vices)
        if ev.trade_proficiencies:
            self._state.trade_proficiencies = list(ev.trade_proficiencies)
        if ev.shelf_inventory:
            self._state.shelf_inventory = [
                WorkerInventoryItem.model_validate(i) for i in ev.shelf_inventory
            ]
        if ev.backroom_inventory:
            self._state.backroom_inventory = [
                WorkerInventoryItem.model_validate(i) for i in ev.backroom_inventory
            ]
        if ev.patience:
            self._state.patience = ev.patience
        self._state.metadata = dict(ev.metadata)

    @handles(NPCWorkerRelieved)
    def handle_relieved(self, ev: NPCWorkerRelieved) -> None:
        """Handle worker dismissal."""
        self._state.status = "relieved"
        self._state.metadata["relieved_reason"] = ev.reason

    @handles(NPCMoodUpdated)
    def handle_mood_updated(self, ev: NPCMoodUpdated) -> None:
        """Handle mood and temperament shift."""
        self._state.mood = ev.mood
        self._state.temperament = ev.temperament
        self._state.patience = max(0, self._state.patience + ev.patience_delta)
        for k, v in ev.metadata.items():
            self._state.metadata[k] = v

    @handles(NPCRelationshipFormed)
    def handle_relationship_formed(self, ev: NPCRelationshipFormed) -> None:
        """Handle social relationship creation or update."""
        existing = next(
            (r for r in self._state.relationships if r.target_npc_id == ev.target_npc_id),
            None,
        )
        if existing:
            existing.relation_type = ev.relation_type
            existing.intensity = ev.intensity
            existing.notes = ev.notes
            existing.metadata = dict(ev.metadata)
        else:
            self._state.relationships.append(
                WorkerRelationship(
                    source_npc_id=ev.source_npc_id,
                    target_npc_id=ev.target_npc_id,
                    relation_type=ev.relation_type,
                    intensity=ev.intensity,
                    notes=ev.notes,
                    metadata=dict(ev.metadata),
                )
            )

    def assign(
        self,
        establishment_id: str,
        role: str,
        wage: int = 1,
        name: str = "",
        campaign_id: str = "",
        traits: BigFivePersonality | dict[str, float] | None = None,
        vices: list[str] | None = None,
        trade_proficiencies: list[str] | None = None,
        shelf_inventory: list[WorkerInventoryItem | dict[str, Any]] | None = None,
        backroom_inventory: list[WorkerInventoryItem | dict[str, Any]] | None = None,
        patience: int = 10,
        metadata: dict[str, Any] | None = None,
    ) -> str:
        """Assign worker to an establishment role and configure inventory."""
        nid = str(self._state.npc_id or self.aggregate_id or uuid4())
        raw_traits = (
            traits.model_dump() if isinstance(traits, BigFivePersonality) else (traits or {})
        )
        raw_shelf = [
            i.model_dump() if isinstance(i, WorkerInventoryItem) else i
            for i in (shelf_inventory or [])
        ]
        raw_backroom = [
            i.model_dump() if isinstance(i, WorkerInventoryItem) else i
            for i in (backroom_inventory or [])
        ]

        self.create_event(
            NPCWorkerAssigned,
            aggregate_id=_to_uuid(nid),
            npc_id=nid,
            establishment_id=str(establishment_id),
            role=role,
            wage=wage,
            assigned_at=datetime.now(UTC).isoformat(),
            name=name or self._state.name,
            campaign_id=str(campaign_id),
            traits=raw_traits,
            vices=vices or [],
            trade_proficiencies=trade_proficiencies or [],
            shelf_inventory=raw_shelf,
            backroom_inventory=raw_backroom,
            patience=patience,
            metadata=metadata or {},
        )
        return nid

    def relieve(self, establishment_id: str = "", reason: str = "") -> None:
        """Relieve worker from establishment duty."""
        nid = str(self._state.npc_id or self.aggregate_id)
        self.create_event(
            NPCWorkerRelieved,
            aggregate_id=_to_uuid(nid),
            npc_id=nid,
            establishment_id=str(establishment_id or self._state.establishment_id),
            reason=reason or "Relieved of duty",
            metadata={},
        )

    def update_mood(
        self,
        mood: str,
        temperament: str,
        patience_delta: int = 0,
        metadata: dict[str, Any] | None = None,
    ) -> None:
        """Shift worker mood, temperament, and patience."""
        nid = str(self._state.npc_id or self.aggregate_id)
        self.create_event(
            NPCMoodUpdated,
            aggregate_id=_to_uuid(nid),
            npc_id=nid,
            mood=mood,
            temperament=temperament,
            patience_delta=patience_delta,
            metadata=metadata or {},
        )

    def form_relationship(
        self,
        target_npc_id: str,
        relation_type: str,
        intensity: float = 1.0,
        notes: str = "",
        metadata: dict[str, Any] | None = None,
    ) -> None:
        """Form or update an interpersonal relationship with another NPC."""
        nid = str(self._state.npc_id or self.aggregate_id)
        self.create_event(
            NPCRelationshipFormed,
            aggregate_id=_to_uuid(nid),
            source_npc_id=nid,
            target_npc_id=str(target_npc_id),
            relation_type=relation_type,
            intensity=intensity,
            notes=notes,
            metadata=metadata or {},
        )

    def refresh_computed_fields(
        self,
        peers: list[NPCWorkerState] | None = None,
        establishment_tier: int = 1,
    ) -> None:
        """Update live computed fields for state projections."""
        self._state.interpersonal_tension = compute_worker_tension(self._state, peers)
        self._state.service_quality_contribution = calculate_service_quality_contribution(
            self._state, establishment_tier
        )
        self._state.redstring_edges = serialize_to_redstring_edges(self._state)

    def to_redstring_edges(self) -> list[dict[str, Any]]:
        """Return serialized redstring knowledge graph edges for this worker."""
        return serialize_to_redstring_edges(self._state)


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
    "calculate_establishment_operations",
    "calculate_service_quality_contribution",
    "compute_supply_chain_dependencies",
    "compute_worker_tension",
    "serialize_to_redstring_edges",
]
