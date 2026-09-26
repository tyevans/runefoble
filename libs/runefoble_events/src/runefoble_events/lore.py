"""Lore domain events for Runefoble worldbuilding and redstring knowledge graph indexing."""

from typing import Any
from uuid import UUID

from pydantic import Field

from runefoble_events.base import BaseRunefobleEvent, register_event


@register_event
class LoreDocumentIngested(BaseRunefobleEvent):
    """Emitted when a new campaign lore markdown/text document is ingested into the knowledge base."""

    event_type: str = "LoreDocumentIngested"
    document_id: UUID = Field(description="Unique document aggregate identifier")
    campaign_id: UUID = Field(description="Campaign to which the lore belongs")
    title: str = Field(description="Title or heading of the lore document")
    content: str = Field(description="Raw markdown/text content of the worldbuilding document")
    is_secret: bool = Field(default=False, description="Whether this lore is restricted to DMs/GMs")
    author_id: str | None = Field(default=None, description="User ID of author or DM")
    metadata: dict[str, Any] = Field(
        default_factory=dict, description="Arbitrary metadata attributes"
    )


@register_event
class EntitiesExtracted(BaseRunefobleEvent):
    """Emitted when entities and relationships are extracted from a lore document via redstring."""

    event_type: str = "EntitiesExtracted"
    document_id: UUID = Field(description="Source document aggregate identifier")
    campaign_id: UUID = Field(description="Campaign to which the lore belongs")
    entities: list[dict[str, Any]] = Field(
        default_factory=list, description="Extracted entity dictionaries"
    )
    relationships: list[dict[str, Any]] = Field(
        default_factory=list, description="Extracted relationship dictionaries"
    )


@register_event
class AliasesConsolidated(BaseRunefobleEvent):
    """Emitted when synonymous entity titles and aliases are consolidated into canonical nodes."""

    event_type: str = "AliasesConsolidated"
    campaign_id: UUID = Field(description="Campaign to which the lore belongs")
    canonical_entity_id: UUID = Field(description="Canonical entity UUID")
    canonical_name: str = Field(description="Canonical name of the entity")
    alias_entity_id: UUID = Field(description="Alias entity UUID merged into canonical")
    alias_name: str = Field(description="Alias name or title")
    document_id: UUID | None = Field(
        default=None, description="Optional document that triggered consolidation"
    )
    reason: str = Field(
        default="alias consolidation", description="Rationale for entity consolidation"
    )
