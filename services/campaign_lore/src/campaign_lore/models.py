"""Domain data models and metadata for campaign lore retrieval."""

from dataclasses import dataclass, field
from datetime import UTC, datetime
from typing import Any
from uuid import UUID

from pydantic import BaseModel
from pydantic import Field as PyField


@dataclass
class DocumentMetadata:
    """Tracked metadata for ingested documents."""

    document_id: UUID
    campaign_id: UUID
    title: str
    content: str
    is_secret: bool
    created_at: datetime = field(default_factory=lambda: datetime.now(UTC))


@dataclass
class LoreSearchResultItem:
    """Individual item returned from hybrid search."""

    text: str
    score: float
    document_id: UUID
    document_title: str
    is_secret: bool
    entities: list[str] = field(default_factory=list)
    graph_context: list[str] = field(default_factory=list)


class WestMarchesState(BaseModel):
    """Event-sourced state for West Marches shared world frontier and stronghold."""

    campaign_id: str = ""
    shared_world_id: str = ""
    world_name: str = "The Frontier Marches"
    frontier_region: str = "The Untamed Wilds"
    description: str = ""
    party_name: str = "Pioneers"
    registered_campaigns: dict[str, str] = PyField(default_factory=dict)
    discoveries: list[dict[str, Any]] = PyField(default_factory=list)
    outposts: dict[str, dict[str, Any]] = PyField(default_factory=dict)
    tavern_board: list[dict[str, Any]] = PyField(default_factory=list)


__all__ = ["DocumentMetadata", "LoreSearchResultItem", "WestMarchesState"]
