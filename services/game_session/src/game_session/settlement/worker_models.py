"""Domain models and schemas for assignable NPC workers and social relationship graphs.

Governed by ADR-0002, ADR-0007, and PRD-0024.
"""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field


class BigFivePersonality(BaseModel):
    """Big Five personality traits (OCEAN) normalized between 0.0 and 1.0."""

    openness: float = Field(default=0.5, ge=0.0, le=1.0)
    conscientiousness: float = Field(default=0.5, ge=0.0, le=1.0)
    extraversion: float = Field(default=0.5, ge=0.0, le=1.0)
    agreeableness: float = Field(default=0.5, ge=0.0, le=1.0)
    neuroticism: float = Field(default=0.5, ge=0.0, le=1.0)


class WorkerInventoryItem(BaseModel):
    """Dynamic inventory item stocked on shelf or locked in the vault/backroom."""

    item_id: str
    name: str = ""
    quantity: int = Field(default=1, alias="stock")
    unit_price: int = Field(default=10, alias="price_gp")
    category: str = "general"
    is_contraband: bool = False
    is_vault_secret: bool = False
    metadata: dict[str, Any] = Field(default_factory=dict)

    model_config = {"populate_by_name": True}


class WorkerRelationship(BaseModel):
    """Interpersonal or mercantile relationship edge in social adjacency graph."""

    source_npc_id: str = ""
    target_npc_id: str = Field(default="", alias="target_npc")
    relation_type: str = Field(default="ally", alias="relation")
    intensity: float = Field(default=1.0, ge=-1.0, le=1.0)
    notes: str = ""
    metadata: dict[str, Any] = Field(default_factory=dict)

    model_config = {"populate_by_name": True}


class NPCWorkerState(BaseModel):
    """Event-sourced domain state of an assignable NPC worker."""

    npc_id: str = ""
    establishment_id: str = ""
    campaign_id: str = ""
    name: str = "NPC Worker"
    role: str = "apprentice"
    wage: int = 1
    status: str = "active"
    assigned_at: str = ""
    traits: BigFivePersonality = Field(default_factory=BigFivePersonality)
    vices: list[str] = Field(default_factory=list)
    trade_proficiencies: list[str] = Field(default_factory=list)
    mood: str = "content"
    temperament: str = "steady"
    patience: int = 10
    shelf_inventory: list[WorkerInventoryItem] = Field(default_factory=list)
    backroom_inventory: list[WorkerInventoryItem] = Field(default_factory=list)
    relationships: list[WorkerRelationship] = Field(default_factory=list)
    interpersonal_tension: float = 0.0
    service_quality_contribution: float = 1.0
    redstring_edges: list[dict[str, Any]] = Field(default_factory=list)
    metadata: dict[str, Any] = Field(default_factory=dict)


class AssignWorkerRequest(BaseModel):
    """Payload to assign an NPC worker to an establishment."""

    npc_id: str | None = None
    name: str = "NPC Worker"
    role: str = "apprentice"
    wage: int = 2
    wage_gold: int | None = None
    traits: BigFivePersonality | dict[str, float] | None = None
    vices: list[str] = Field(default_factory=list)
    trade_proficiencies: list[str] = Field(default_factory=list)
    mood: str = "content"
    temperament: str = "steady"
    patience: int = 10
    shelf_inventory: list[dict[str, Any] | WorkerInventoryItem] = Field(default_factory=list)
    backroom_inventory: list[dict[str, Any] | WorkerInventoryItem] = Field(default_factory=list)
    vault_inventory: list[dict[str, Any] | WorkerInventoryItem] | None = None
    relationships: list[dict[str, Any] | WorkerRelationship] = Field(default_factory=list)
    metadata: dict[str, Any] = Field(default_factory=dict)


class UpdateWorkerMoodRequest(BaseModel):
    """Payload to modify an NPC worker's temperament, mood, and patience."""

    mood: str
    temperament: str
    patience_delta: int = 0
    metadata: dict[str, Any] = Field(default_factory=dict)


class FormRelationshipRequest(BaseModel):
    """Payload to record an interpersonal tie between two NPCs."""

    target_npc_id: str = Field(default="", alias="target_npc")
    relation_type: str = Field(default="ally", alias="relation")
    intensity: float = 1.0
    notes: str = ""
    metadata: dict[str, Any] = Field(default_factory=dict)

    model_config = {"populate_by_name": True}


class RelieveWorkerRequest(BaseModel):
    """Payload to relieve a worker from establishment duty."""

    reason: str = "Contract concluded"
    metadata: dict[str, Any] = Field(default_factory=dict)


class EstablishmentOperationsSummary(BaseModel):
    """Projected establishment operational metrics based on active staff."""

    total_staff: int
    total_wages: int
    net_operating_cost: int
    average_morale: float
    interpersonal_tension_index: float
    projected_service_quality: float
    service_quality_tier: str


class EstablishmentRosterResponse(BaseModel):
    """Full staff roster response with operations and social graph edges."""

    establishment_id: str
    workers: list[NPCWorkerState] = Field(default_factory=list)
    operations: EstablishmentOperationsSummary
    projected_service_quality: float
    service_quality_tier: str
    social_graph_edges: list[dict[str, Any]] = Field(default_factory=list)
