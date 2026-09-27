"""API routes for Collaborative Party Codex, Secret Notes, and Redstring Lore Links."""

from typing import Annotated, Any
from uuid import UUID, uuid4

from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel, Field
from runefoble_auth.spicedb import SpiceDBClient
from runefoble_platform.event_sourcing import AggregateRepository

from campaign_lore.codex import CodexCrossReferencer
from campaign_lore.codex_aggregate import CodexAggregate
from campaign_lore.dependencies import (
    check_user_can_edit_codex_entry,
    check_user_can_view_campaign,
    check_user_can_view_codex_entry,
    get_campaign_codex_index,
    get_codex_referencer,
    get_codex_repo,
    get_current_user_id,
    get_spicedb_client,
)

router = APIRouter(prefix="/api/v1/campaigns/{campaign_id}/codex", tags=["Party Codex"])


class PublishCodexEntryRequest(BaseModel):
    """Payload to publish or record a new party codex entry."""

    title: str = Field(description="Title of journal note or lore chronicle")
    content: str = Field(description="Markdown body of the entry")
    privacy: str = Field(
        default="private", description="Visibility: private, party_shared, or public"
    )
    era: str | None = Field(default=None, description="Campaign era or chronological session tag")
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


@router.post("/entries", response_model=dict[str, Any], status_code=status.HTTP_201_CREATED)
async def publish_entry(
    campaign_id: UUID,
    payload: PublishCodexEntryRequest,
    user_id: Annotated[str | None, Depends(get_current_user_id)],
    repo: Annotated[AggregateRepository[CodexAggregate], Depends(get_codex_repo)],
    referencer: Annotated[CodexCrossReferencer, Depends(get_codex_referencer)],
    codex_index: Annotated[dict[UUID, list[UUID]], Depends(get_campaign_codex_index)],
    spicedb: Annotated[SpiceDBClient, Depends(get_spicedb_client)],
) -> dict[str, Any]:
    """Publish a new journal or secret codex entry with automated redstring hyperlinking."""
    can_view = await check_user_can_view_campaign(user_id, campaign_id, spicedb)
    if not can_view:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Forbidden: Cannot access campaign codex.",
        )

    author_id = user_id or "anonymous_author"
    entry_id = uuid4()

    # Automatically scan content and cross-reference entities against redstring knowledge graph
    cross_res = await referencer.cross_reference_content(campaign_id, payload.content)
    meta = dict(payload.metadata)
    meta["cross_references"] = cross_res["linked_entities"]
    meta["illuminated_content"] = cross_res["illuminated_content"]

    aggregate = CodexAggregate(entry_id)
    aggregate.publish(
        campaign_id=campaign_id,
        title=payload.title,
        content=payload.content,
        author_id=author_id,
        privacy=payload.privacy,
        era=payload.era,
        tags=payload.tags,
        linked_entity_ids=cross_res["linked_entity_ids"],
        metadata=meta,
    )
    await repo.save(aggregate)

    # Register in campaign index
    if campaign_id not in codex_index:
        codex_index[campaign_id] = []
    codex_index[campaign_id].append(entry_id)

    # Write Zanzibar relationship tuples
    str_entry_id = str(entry_id)
    await spicedb.write_relationship(
        resource_type="codex_entry",
        resource_id=str_entry_id,
        relation="author",
        subject_type="user",
        subject_id=author_id,
    )
    await spicedb.write_relationship(
        resource_type="codex_entry",
        resource_id=str_entry_id,
        relation="editor",
        subject_type="user",
        subject_id=author_id,
    )
    await spicedb.write_relationship(
        resource_type="codex_entry",
        resource_id=str_entry_id,
        relation="campaign",
        subject_type="campaign",
        subject_id=str(campaign_id),
    )

    if payload.privacy == "party_shared":
        await spicedb.write_relationship(
            resource_type="codex_entry",
            resource_id=str_entry_id,
            relation="party_shared",
            subject_type="campaign",
            subject_id=str(campaign_id),
        )
    elif payload.privacy == "public":
        await spicedb.write_relationship(
            resource_type="codex_entry",
            resource_id=str_entry_id,
            relation="public",
            subject_type="campaign",
            subject_id=str(campaign_id),
        )

    return {
        "entry_id": str(entry_id),
        "campaign_id": str(campaign_id),
        "title": payload.title,
        "content": payload.content,
        "illuminated_content": cross_res["illuminated_content"],
        "privacy": payload.privacy,
        "author_id": author_id,
        "era": payload.era,
        "tags": payload.tags,
        "linked_entities": cross_res["linked_entities"],
        "status": "published",
    }


@router.get("/entries", response_model=list[dict[str, Any]])
async def list_entries(
    campaign_id: UUID,
    user_id: Annotated[str | None, Depends(get_current_user_id)],
    repo: Annotated[AggregateRepository[CodexAggregate], Depends(get_codex_repo)],
    codex_index: Annotated[dict[UUID, list[UUID]], Depends(get_campaign_codex_index)],
    spicedb: Annotated[SpiceDBClient, Depends(get_spicedb_client)],
    era: str | None = Query(default=None, description="Era filter"),
    tag: str | None = Query(default=None, description="Tag filter"),
    search: str | None = Query(default=None, description="Keyword search"),
) -> list[dict[str, Any]]:
    """List codex entries visible to the authenticated user, enforcing SpiceDB Zanzibar privacy checks."""
    can_view = await check_user_can_view_campaign(user_id, campaign_id, spicedb)
    if not can_view:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Forbidden: Cannot view campaign codex.",
        )

    entry_ids = codex_index.get(campaign_id, [])
    visible_entries: list[dict[str, Any]] = []

    for eid in entry_ids:
        try:
            aggregate = await repo.load(eid)
            state = aggregate.state
        except Exception:
            continue

        # Enforce SpiceDB Zanzibar permission check: omit private notes if not authorized
        can_read = await check_user_can_view_codex_entry(user_id, state, campaign_id, spicedb)
        if not can_read:
            continue

        # Apply filtering
        if era and (not state.era or era.lower() not in state.era.lower()):
            continue
        if tag and tag not in state.tags:
            continue
        if search:
            q = search.lower()
            if q not in state.title.lower() and q not in state.content.lower():
                continue

        visible_entries.append(
            {
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
        )

    return visible_entries


@router.get("/entries/{entry_id}", response_model=dict[str, Any])
async def get_entry(
    campaign_id: UUID,
    entry_id: UUID,
    user_id: Annotated[str | None, Depends(get_current_user_id)],
    repo: Annotated[AggregateRepository[CodexAggregate], Depends(get_codex_repo)],
    spicedb: Annotated[SpiceDBClient, Depends(get_spicedb_client)],
) -> dict[str, Any]:
    """Retrieve an illuminated codex entry by ID, enforcing SpiceDB Zanzibar access control."""
    try:
        aggregate = await repo.load(entry_id)
        state = aggregate.state
    except Exception as exc:
        raise HTTPException(status_code=404, detail="Codex entry not found") from exc

    # Enforce SpiceDB Zanzibar authorization
    can_read = await check_user_can_view_codex_entry(user_id, state, campaign_id, spicedb)
    if not can_read:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Forbidden: SpiceDB Zanzibar policy denies access to this private codex entry.",
        )

    return {
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
        "metadata": state.metadata,
    }


@router.patch("/entries/{entry_id}", response_model=dict[str, Any])
async def update_entry(
    campaign_id: UUID,
    entry_id: UUID,
    payload: UpdateCodexEntryRequest,
    user_id: Annotated[str | None, Depends(get_current_user_id)],
    repo: Annotated[AggregateRepository[CodexAggregate], Depends(get_codex_repo)],
    referencer: Annotated[CodexCrossReferencer, Depends(get_codex_referencer)],
    spicedb: Annotated[SpiceDBClient, Depends(get_spicedb_client)],
) -> dict[str, Any]:
    """Update codex entry text or revise privacy status."""
    try:
        aggregate = await repo.load(entry_id)
        state = aggregate.state
    except Exception as exc:
        raise HTTPException(status_code=404, detail="Codex entry not found") from exc

    can_edit = await check_user_can_edit_codex_entry(user_id, state, campaign_id, spicedb)
    if not can_edit:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Forbidden: Not authorized to edit this codex entry.",
        )

    meta = dict(state.metadata)
    new_content = payload.content if payload.content is not None else state.content

    if payload.content is not None:
        cross_res = await referencer.cross_reference_content(campaign_id, new_content)
        meta["cross_references"] = cross_res["linked_entities"]
        meta["illuminated_content"] = cross_res["illuminated_content"]

    aggregate.update(
        title=payload.title,
        content=payload.content,
        privacy=payload.privacy,
        era=payload.era,
        tags=payload.tags,
        updated_by=user_id,
        metadata=meta,
    )
    await repo.save(aggregate)

    # If privacy changed, update SpiceDB relationships
    if payload.privacy and payload.privacy != state.privacy:
        str_entry_id = str(entry_id)
        # Delete old relations if needed
        if state.privacy == "party_shared":
            await spicedb.delete_relationship(
                "codex_entry", str_entry_id, "party_shared", "campaign", str(campaign_id)
            )
        elif state.privacy == "public":
            await spicedb.delete_relationship(
                "codex_entry", str_entry_id, "public", "campaign", str(campaign_id)
            )

        # Write new relations
        if payload.privacy == "party_shared":
            await spicedb.write_relationship(
                "codex_entry", str_entry_id, "party_shared", "campaign", str(campaign_id)
            )
        elif payload.privacy == "public":
            await spicedb.write_relationship(
                "codex_entry", str_entry_id, "public", "campaign", str(campaign_id)
            )

    return {
        "entry_id": str(entry_id),
        "status": "updated",
        "privacy": aggregate.state.privacy,
        "title": aggregate.state.title,
    }
