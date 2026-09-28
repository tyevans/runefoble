"""Event-sourced CodexAggregate using eventsource-py."""

from typing import Any
from uuid import UUID, uuid4

from eventsource.domain.aggregate import DeclarativeAggregate
from eventsource.domain.decorators import handles
from pydantic import BaseModel, Field
from runefoble_events.events import CodexEntryPublished, CodexEntryUpdated


class CodexEntryState(BaseModel):
    """Internal state representation for an illuminated collaborative party codex entry."""

    entry_id: UUID
    campaign_id: UUID
    title: str
    content: str
    privacy: str = "private"
    author_id: str
    era: str | None = None
    tags: list[str] = Field(default_factory=list)
    linked_entity_ids: list[str] = Field(default_factory=list)
    cross_references: list[dict[str, Any]] = Field(default_factory=list)
    metadata: dict[str, Any] = Field(default_factory=dict)


class CodexAggregate(DeclarativeAggregate[CodexEntryState]):
    """Event-sourced aggregate managing party codex entry revisions, privacy, and lore links."""

    aggregate_type = "Codex"
    requires_creation_event = True

    def publish(
        self,
        campaign_id: UUID,
        title: str,
        content: str,
        author_id: str,
        privacy: str = "private",
        era: str | None = None,
        tags: list[str] | None = None,
        linked_entity_ids: list[str] | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> None:
        """Publish a new journal or secret codex entry."""
        self.create_event(
            CodexEntryPublished,
            aggregate_id=self.aggregate_id,
            entry_id=self.aggregate_id,
            campaign_id=campaign_id,
            title=title,
            content=content,
            privacy=privacy,
            author_id=author_id,
            era=era,
            tags=tags or [],
            linked_entity_ids=linked_entity_ids or [],
            metadata=metadata or {},
        )

    def update(
        self,
        title: str | None = None,
        content: str | None = None,
        privacy: str | None = None,
        era: str | None = None,
        tags: list[str] | None = None,
        linked_entity_ids: list[str] | None = None,
        updated_by: str | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> None:
        """Update an existing codex entry content or privacy."""
        self.create_event(
            CodexEntryUpdated,
            aggregate_id=self.aggregate_id,
            entry_id=self.aggregate_id,
            campaign_id=self.state.campaign_id,
            title=title,
            content=content,
            privacy=privacy,
            era=era,
            tags=tags,
            linked_entity_ids=linked_entity_ids,
            updated_by=updated_by,
            metadata=metadata,
        )

    @classmethod
    def create(
        cls,
        campaign_id: UUID,
        payload: Any,
        author_id: str,
        metadata: dict[str, Any],
        linked_entity_ids: list[str],
    ) -> "CodexAggregate":
        """Factory creating a new initialized CodexAggregate from payload and enriched metadata."""
        agg = cls(uuid4())
        agg.publish(
            campaign_id=campaign_id,
            title=payload.title,
            content=payload.content,
            author_id=author_id,
            privacy=payload.privacy,
            era=payload.era,
            tags=payload.tags,
            linked_entity_ids=linked_entity_ids,
            metadata=metadata,
        )
        return agg

    def apply_update(
        self,
        payload: Any,
        updated_by: str | None,
        metadata: dict[str, Any],
    ) -> None:
        """Apply domain update payload with revised metadata and entity links."""
        self.update(
            title=payload.title,
            content=payload.content,
            privacy=payload.privacy,
            era=payload.era,
            tags=payload.tags,
            updated_by=updated_by,
            metadata=metadata,
        )

    # -----------------------------------------------------------------------
    # Event Handlers (@handles)
    # -----------------------------------------------------------------------

    @handles(CodexEntryPublished)
    def _on_published(self, event: CodexEntryPublished) -> None:
        self._state = CodexEntryState(
            entry_id=event.entry_id,
            campaign_id=event.campaign_id,
            title=event.title,
            content=event.content,
            privacy=event.privacy,
            author_id=event.author_id,
            era=event.era,
            tags=event.tags,
            linked_entity_ids=event.linked_entity_ids,
            cross_references=event.metadata.get("cross_references", []),
            metadata=event.metadata,
        )

    @handles(CodexEntryUpdated)
    def _on_updated(self, event: CodexEntryUpdated) -> None:
        if event.title is not None:
            self.state.title = event.title
        if event.content is not None:
            self.state.content = event.content
        if event.privacy is not None:
            self.state.privacy = event.privacy
        if event.era is not None:
            self.state.era = event.era
        if event.tags is not None:
            self.state.tags = event.tags
        if event.linked_entity_ids is not None:
            self.state.linked_entity_ids = event.linked_entity_ids
        if event.metadata is not None:
            self.state.metadata.update(event.metadata)
            if "cross_references" in event.metadata:
                self.state.cross_references = event.metadata["cross_references"]
