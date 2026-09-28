"""API routes for Codex entry publishing, retrieval, listing, and updates."""

from __future__ import annotations

from typing import Annotated, Any
from uuid import UUID

from fastapi import APIRouter, Depends, Query, status

from campaign_lore.codex import CodexCrossReferencer
from campaign_lore.codex_aggregate import CodexAggregate
from campaign_lore.dependencies import (
    CodexSessionDeps,
    get_campaign_codex_index,
    get_codex_referencer,
    load_codex_entry,
    require_campaign_view,
)
from campaign_lore.routers.codex.referencing import enrich_entry_metadata
from campaign_lore.routers.codex.schemas import (
    PublishCodexEntryRequest,
    UpdateCodexEntryRequest,
    filter_entry_match,
    format_codex_entry,
)

router = APIRouter()


@router.post("/entries", response_model=dict[str, Any], status_code=status.HTTP_201_CREATED)
async def publish_entry(
    campaign_id: UUID,
    payload: PublishCodexEntryRequest,
    deps: Annotated[CodexSessionDeps, Depends()],
    ref: Annotated[CodexCrossReferencer, Depends(get_codex_referencer)],
    idx: Annotated[dict[UUID, list[UUID]], Depends(get_campaign_codex_index)],
) -> dict[str, Any]:
    """Publish a new journal or secret codex entry with automated redstring hyperlinking."""
    await require_campaign_view(deps.user_id, campaign_id, deps.spicedb)
    author_id = deps.user_id or "anonymous_author"
    meta, entity_ids = await enrich_entry_metadata(
        ref, campaign_id, payload.content, payload.metadata
    )
    agg = CodexAggregate.create(campaign_id, payload, author_id, meta, entity_ids)
    await deps.persist_new_entry(agg, campaign_id, author_id, payload.privacy, idx)
    return {**format_codex_entry(agg.state), "status": "published"}


@router.get("/entries", response_model=list[dict[str, Any]])
async def list_entries(
    campaign_id: UUID,
    deps: Annotated[CodexSessionDeps, Depends()],
    idx: Annotated[dict[UUID, list[UUID]], Depends(get_campaign_codex_index)],
    era: str | None = Query(default=None),
    tag: str | None = Query(default=None),
    search: str | None = Query(default=None),
) -> list[dict[str, Any]]:
    """List codex entries visible to authenticated user under SpiceDB Zanzibar privacy checks."""
    await require_campaign_view(deps.user_id, campaign_id, deps.spicedb)
    results = []
    for eid in idx.get(campaign_id, []):
        try:
            st = (await deps.repo.load(eid)).state
        except Exception:
            continue
        if await deps.can_view(st, campaign_id) and filter_entry_match(st, era, tag, search):
            results.append(format_codex_entry(st))
    return results


@router.get("/entries/{entry_id}", response_model=dict[str, Any])
async def get_entry(
    campaign_id: UUID,
    entry_id: UUID,
    deps: Annotated[CodexSessionDeps, Depends()],
) -> dict[str, Any]:
    """Retrieve an illuminated codex entry by ID, enforcing SpiceDB Zanzibar access control."""
    agg = await load_codex_entry(campaign_id, entry_id, deps.user_id, deps.repo, deps.spicedb)
    return format_codex_entry(agg.state, include_metadata=True)


@router.patch("/entries/{entry_id}", response_model=dict[str, Any])
async def update_entry(
    campaign_id: UUID,
    entry_id: UUID,
    payload: UpdateCodexEntryRequest,
    deps: Annotated[CodexSessionDeps, Depends()],
    ref: Annotated[CodexCrossReferencer, Depends(get_codex_referencer)],
) -> dict[str, Any]:
    """Update codex entry text or revise privacy status."""
    agg = await load_codex_entry(
        campaign_id, entry_id, deps.user_id, deps.repo, deps.spicedb, for_edit=True
    )
    meta = dict(agg.state.metadata)
    new_content = payload.content if payload.content is not None else agg.state.content
    if payload.content is not None:
        meta, _ = await enrich_entry_metadata(ref, campaign_id, new_content, agg.state.metadata)

    old_privacy = agg.state.privacy
    agg.apply_update(payload, deps.user_id, meta)
    await deps.persist_updated_entry(agg, campaign_id, entry_id, old_privacy, payload.privacy)
    return {
        "entry_id": str(entry_id),
        "status": "updated",
        "privacy": agg.state.privacy,
        "title": agg.state.title,
    }
