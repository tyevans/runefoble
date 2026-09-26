"""Event-sourced LoreDocument aggregate using eventsource-py."""

from typing import Any
from uuid import UUID

from eventsource.domain.aggregate import DeclarativeAggregate
from eventsource.domain.decorators import handles
from pydantic import BaseModel, Field
from runefoble_events.events import (
    AliasesConsolidated,
    EntitiesExtracted,
    LoreDocumentIngested,
)


class LoreDocumentState(BaseModel):
    """Internal state representation for an ingested campaign lore document."""

    document_id: UUID
    campaign_id: UUID
    title: str
    content: str
    is_secret: bool = False
    author_id: str | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)
    entities: list[dict[str, Any]] = Field(default_factory=list)
    relationships: list[dict[str, Any]] = Field(default_factory=list)
    consolidated_aliases: list[dict[str, Any]] = Field(default_factory=list)


class LoreDocumentAggregate(DeclarativeAggregate[LoreDocumentState]):
    """Event-sourced aggregate managing lore document lifecycle, extractions, and aliases."""

    aggregate_type = "LoreDocument"
    requires_creation_event = True

    def ingest(
        self,
        campaign_id: UUID,
        title: str,
        content: str,
        is_secret: bool = False,
        author_id: str | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> None:
        """Ingest a new worldbuilding document."""
        self.create_event(
            LoreDocumentIngested,
            aggregate_id=self.aggregate_id,
            document_id=self.aggregate_id,
            campaign_id=campaign_id,
            title=title,
            content=content,
            is_secret=is_secret,
            author_id=author_id,
            metadata=metadata or {},
        )

    def record_extracted_entities(
        self,
        entities: list[dict[str, Any]],
        relationships: list[dict[str, Any]],
    ) -> None:
        """Record entities and relationships extracted from the document text via redstring."""
        self.create_event(
            EntitiesExtracted,
            aggregate_id=self.aggregate_id,
            document_id=self.aggregate_id,
            campaign_id=self.state.campaign_id,
            entities=entities,
            relationships=relationships,
        )

    def consolidate_alias(
        self,
        canonical_entity_id: UUID,
        canonical_name: str,
        alias_entity_id: UUID,
        alias_name: str,
        reason: str = "alias consolidation",
    ) -> None:
        """Consolidate an alias entity into its canonical entity node."""
        self.create_event(
            AliasesConsolidated,
            aggregate_id=self.aggregate_id,
            document_id=self.aggregate_id,
            campaign_id=self.state.campaign_id,
            canonical_entity_id=canonical_entity_id,
            canonical_name=canonical_name,
            alias_entity_id=alias_entity_id,
            alias_name=alias_name,
            reason=reason,
        )

    # -----------------------------------------------------------------------
    # Event Handlers (@handles)
    # -----------------------------------------------------------------------

    @handles(LoreDocumentIngested)
    def _on_ingested(self, event: LoreDocumentIngested) -> None:
        self._state = LoreDocumentState(
            document_id=event.document_id,
            campaign_id=event.campaign_id,
            title=event.title,
            content=event.content,
            is_secret=event.is_secret,
            author_id=event.author_id,
            metadata=event.metadata,
        )

    @handles(EntitiesExtracted)
    def _on_entities_extracted(self, event: EntitiesExtracted) -> None:
        self.state.entities.extend(event.entities)
        self.state.relationships.extend(event.relationships)

    @handles(AliasesConsolidated)
    def _on_aliases_consolidated(self, event: AliasesConsolidated) -> None:
        self.state.consolidated_aliases.append(
            {
                "canonical_entity_id": str(event.canonical_entity_id),
                "canonical_name": event.canonical_name,
                "alias_entity_id": str(event.alias_entity_id),
                "alias_name": event.alias_name,
                "reason": event.reason,
            }
        )
