"""Domain events for settlement establishment NPC workers and social relationship graphs.

Governed by ADR-0002, ADR-0007, ADR-0011, and PRD-0024.
"""

from __future__ import annotations

from typing import Any, Literal
from uuid import UUID, uuid4

from pydantic import Field

from runefoble_events.base import BaseRunefobleEvent, register_event


@register_event("runefoble.events.game_session.npc_worker_assigned")
class NPCWorkerAssigned(BaseRunefobleEvent):
    """Emitted when an NPC is hired or assigned to a role in an establishment."""

    aggregate_type: str = "NPCWorker"
    aggregate_id: UUID = Field(default_factory=uuid4)
    event_type: str = "runefoble.events.game_session.npc_worker_assigned"
    npc_id: str
    establishment_id: str
    role: str
    wage: int = 1
    assigned_at: str = ""
    name: str = ""
    campaign_id: str = ""
    traits: dict[str, float] = Field(default_factory=dict)
    vices: list[str] = Field(default_factory=list)
    trade_proficiencies: list[str] = Field(default_factory=list)
    shelf_inventory: list[dict[str, Any]] = Field(default_factory=list)
    backroom_inventory: list[dict[str, Any]] = Field(default_factory=list)
    patience: int = 10
    metadata: dict[str, Any] = Field(default_factory=dict)


@register_event("runefoble.events.game_session.npc_worker_relieved")
class NPCWorkerRelieved(BaseRunefobleEvent):
    """Emitted when an NPC worker is relieved, dismissed, or fired from an establishment."""

    aggregate_type: str = "NPCWorker"
    aggregate_id: UUID = Field(default_factory=uuid4)
    event_type: str = "runefoble.events.game_session.npc_worker_relieved"
    npc_id: str
    establishment_id: str
    reason: str = ""
    metadata: dict[str, Any] = Field(default_factory=dict)


@register_event("runefoble.events.game_session.npc_mood_updated")
class NPCMoodUpdated(BaseRunefobleEvent):
    """Emitted when an NPC worker's mood, temperament, or patience shifts."""

    aggregate_type: str = "NPCWorker"
    aggregate_id: UUID = Field(default_factory=uuid4)
    event_type: str = "runefoble.events.game_session.npc_mood_updated"
    npc_id: str
    mood: str
    temperament: str
    patience_delta: int = 0
    metadata: dict[str, Any] = Field(default_factory=dict)


@register_event("runefoble.events.game_session.npc_relationship_formed")
class NPCRelationshipFormed(BaseRunefobleEvent):
    """Emitted when an interpersonal social or supply tie is established between NPCs."""

    aggregate_type: str = "NPCWorker"
    aggregate_id: UUID = Field(default_factory=uuid4)
    event_type: str = "runefoble.events.game_session.npc_relationship_formed"
    source_npc_id: str
    target_npc_id: str
    relation_type: str  # ally, rival, debtor, lover, mentor, supplier, apprentice
    intensity: float = 1.0
    notes: str = ""
    metadata: dict[str, Any] = Field(default_factory=dict)


@register_event("runefoble.events.game_session.npc_worker_inventory_restocked")
class NPCWorkerInventoryRestocked(BaseRunefobleEvent):
    """Emitted when a manager restocks an item on an NPC worker's shelf or in the backroom."""

    aggregate_type: str = "NPCWorker"
    aggregate_id: UUID = Field(default_factory=uuid4)
    event_type: str = "runefoble.events.game_session.npc_worker_inventory_restocked"
    npc_id: str
    destination: Literal["shelf", "backroom"]
    item: dict[str, Any]


__all__ = [
    "NPCMoodUpdated",
    "NPCRelationshipFormed",
    "NPCWorkerAssigned",
    "NPCWorkerInventoryRestocked",
    "NPCWorkerRelieved",
]
