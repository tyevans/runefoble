"""API routes and helpers for cross-referencing and entity mention resolution."""

from __future__ import annotations

from typing import Annotated, Any
from uuid import UUID

from fastapi import APIRouter, Depends
from runefoble_auth.spicedb import SpiceDBClient

from campaign_lore.codex import CodexCrossReferencer
from campaign_lore.dependencies import (
    CodexSessionDeps,
    get_codex_referencer,
    get_current_user_id,
    get_spicedb_client,
    load_codex_entry,
    require_campaign_view,
)
from campaign_lore.routers.codex.schemas import CrossReferenceContentRequest

router = APIRouter()


async def enrich_entry_metadata(
    referencer: CodexCrossReferencer,
    campaign_id: UUID,
    content: str,
    base_metadata: dict[str, Any] | None = None,
) -> tuple[dict[str, Any], list[str]]:
    """Scan entry markdown, identify entity references, and generate hyperlinked metadata."""
    cross_res = await referencer.cross_reference_content(campaign_id, content)
    meta = dict(base_metadata or {})
    meta["cross_references"] = cross_res["linked_entities"]
    meta["illuminated_content"] = cross_res["illuminated_content"]
    return meta, cross_res["linked_entity_ids"]


@router.get("/entries/{entry_id}/references", response_model=dict[str, Any])
async def get_entry_references(
    campaign_id: UUID, entry_id: UUID, deps: Annotated[CodexSessionDeps, Depends()]
) -> dict[str, Any]:
    """Retrieve entity cross-references and mention links for a codex entry."""
    agg = await load_codex_entry(campaign_id, entry_id, deps.user_id, deps.repo, deps.spicedb)
    st = agg.state
    return {
        "entry_id": str(st.entry_id),
        "campaign_id": str(st.campaign_id),
        "linked_entities": st.cross_references,
        "linked_entity_ids": st.linked_entity_ids,
        "illuminated_content": st.metadata.get("illuminated_content", st.content),
    }


@router.post("/references/extract", response_model=dict[str, Any])
async def extract_references(
    campaign_id: UUID,
    payload: CrossReferenceContentRequest,
    user_id: Annotated[str | None, Depends(get_current_user_id)],
    referencer: Annotated[CodexCrossReferencer, Depends(get_codex_referencer)],
    spicedb: Annotated[SpiceDBClient, Depends(get_spicedb_client)],
) -> dict[str, Any]:
    """Scan text and extract redstring entity mentions and hyperlinked content."""
    await require_campaign_view(user_id, campaign_id, spicedb)
    return await referencer.cross_reference_content(campaign_id, payload.content)
