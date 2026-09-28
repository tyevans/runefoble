"""Pydantic schemas and serialization helpers for Collaborative Party Codex."""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field

from campaign_lore.codex_aggregate import CodexEntryState


class PublishCodexEntryRequest(BaseModel):
    """Payload to publish or record a new party codex entry."""

    title: str = Field(description="Title of journal note or lore chronicle")
    content: str = Field(description="Markdown body of the entry")
    privacy: str = Field(default="private", description="Visibility: private, party_shared, public")
    era: str | None = Field(default=None, description="Campaign era or session tag")
    tags: list[str] = Field(default_factory=list, description="Categorization tags")
    metadata: dict[str, Any] = Field(default_factory=dict, description="Arbitrary attributes")


class UpdateCodexEntryRequest(BaseModel):
    """Payload to update an existing codex entry."""

    title: str | None = None
    content: str | None = None
    privacy: str | None = None
    era: str | None = None
    tags: list[str] | None = None
    metadata: dict[str, Any] | None = None


class CrossReferenceContentRequest(BaseModel):
    """Payload to scan text and resolve redstring entity references."""

    content: str = Field(description="Content text to scan for entity mentions")


class CrossReferenceResponse(BaseModel):
    """Response containing extracted entity links and illuminated content."""

    illuminated_content: str
    linked_entities: list[dict[str, Any]]
    linked_entity_ids: list[str]


def format_codex_entry(state: CodexEntryState, include_metadata: bool = False) -> dict[str, Any]:
    """Serialize CodexEntryState to standard API dictionary."""
    data = {
        "entry_id": str(state.entry_id),
        "campaign_id": str(state.campaign_id),
        "title": state.title,
        "content": state.content,
        "illuminated_content": state.metadata.get("illuminated_content", state.content),
        "privacy": state.privacy,
        "author_id": state.author_id,
        "era": state.era,
        "tags": state.tags,
        "linked_entities": state.cross_references,
    }
    if include_metadata:
        data["metadata"] = state.metadata
    return data


def filter_entry_match(
    st: CodexEntryState, era: str | None, tag: str | None, search: str | None
) -> bool:
    """Evaluate era, tag, and search query filters against a codex entry."""
    if era and (not st.era or era.lower() not in st.era.lower()):
        return False
    if tag and tag not in st.tags:
        return False
    return not (
        search
        and search.lower() not in st.title.lower()
        and search.lower() not in st.content.lower()
    )
