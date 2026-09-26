"""Domain data models and metadata for campaign lore retrieval."""

from dataclasses import dataclass, field
from datetime import UTC, datetime
from uuid import UUID


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


__all__ = ["DocumentMetadata", "LoreSearchResultItem"]
