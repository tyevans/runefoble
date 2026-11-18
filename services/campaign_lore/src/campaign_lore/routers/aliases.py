"""Alias consolidation router for knowledge graph entities."""

from typing import Annotated
from uuid import UUID

from eventsource import AggregateNotFoundError
from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field
from redstring import DoubleMergeError, MergeIntoAliasError
from runefoble_auth.factory import get_spicedb_client
from runefoble_auth.spicedb import SpiceDBClient
from runefoble_platform.event_sourcing import AggregateRepository

from campaign_lore.aggregate import LoreDocumentAggregate
from campaign_lore.dependencies import (
    get_repo,
    get_retrieval_engine,
)
from campaign_lore.identity import CallerId, get_campaign_principal
from campaign_lore.permissions import check_user_can_run_session
from campaign_lore.retrieval import LoreRetrievalEngine

router = APIRouter(tags=["Entity Aliases"], dependencies=[Depends(get_campaign_principal)])


class ConsolidateAliasRequest(BaseModel):
    """Payload to consolidate an alias into a canonical entity node."""

    campaign_id: UUID = Field(description="Campaign UUID")
    canonical_name: str = Field(description="Canonical entity name (e.g. 'Sir Gareth')")
    alias_name: str = Field(description="Alias name or title (e.g. 'The Silver Knight')")
    reason: str = Field(default="alias consolidation", description="Rationale for consolidation")
    document_id: UUID = Field(description="Document aggregate that records the consolidation")


class ConsolidateAliasResponse(BaseModel):
    """Response returned upon alias consolidation."""

    campaign_id: UUID
    canonical_entity_id: UUID
    canonical_name: str
    alias_entity_id: UUID
    alias_name: str
    reason: str
    status: str = "consolidated"


class ResolveAliasResponse(BaseModel):
    """Response returned when resolving an alias."""

    campaign_id: UUID
    input_name: str
    canonical_name: str
    is_alias: bool


_CONSOLIDATE_RESPONSES = {
    409: {"description": "The alias or canonical entity is already merged. Nothing is recorded."},
    503: {"description": "campaign_lore is not started"},
}


@router.post(
    "/api/v1/lore/aliases/consolidate",
    response_model=ConsolidateAliasResponse,
    responses=_CONSOLIDATE_RESPONSES,
)
async def consolidate_alias(
    req: ConsolidateAliasRequest,
    user_id: CallerId,
    retrieval_engine: Annotated[LoreRetrievalEngine, Depends(get_retrieval_engine)],
    repo: Annotated[AggregateRepository[LoreDocumentAggregate], Depends(get_repo)],
    spicedb: Annotated[SpiceDBClient, Depends(get_spicedb_client)],
) -> ConsolidateAliasResponse:
    """Merge an alias title into a canonical entity node and record it on the document."""
    if not await check_user_can_run_session(user_id, req.campaign_id, spicedb):
        raise HTTPException(
            status_code=403,
            detail="Forbidden: Only campaign run_session members can consolidate aliases.",
        )
    try:
        document = await repo.load(req.document_id)
    except AggregateNotFoundError as exc:
        raise HTTPException(status_code=404, detail="Lore document not found") from exc
    if document.state.campaign_id != req.campaign_id:
        raise HTTPException(status_code=404, detail="Lore document not found")

    try:
        canon_id, alias_id = await retrieval_engine.consolidate_alias(
            campaign_id=req.campaign_id,
            canonical_name=req.canonical_name,
            alias_name=req.alias_name,
            document_id=req.document_id,
            reason=req.reason,
        )
    except (DoubleMergeError, MergeIntoAliasError) as exc:
        # A repeated or circular merge is a client conflict. Redstring refused it before writing.
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    document.consolidate_alias(
        canonical_entity_id=canon_id,
        canonical_name=req.canonical_name,
        alias_entity_id=alias_id,
        alias_name=req.alias_name,
        reason=req.reason,
    )
    await repo.save(document)

    return ConsolidateAliasResponse(
        campaign_id=req.campaign_id,
        canonical_entity_id=canon_id,
        canonical_name=req.canonical_name,
        alias_entity_id=alias_id,
        alias_name=req.alias_name,
        reason=req.reason,
        status="consolidated",
    )


@router.get("/api/v1/lore/aliases/resolve", response_model=ResolveAliasResponse)
async def resolve_alias(
    campaign_id: UUID,
    retrieval_engine: Annotated[LoreRetrievalEngine, Depends(get_retrieval_engine)],
    name: str = Query(..., description="Entity name or alias to resolve"),
) -> ResolveAliasResponse:
    """Resolve an entity title or alias to its canonical node."""
    canon_name = await retrieval_engine.resolve_alias(campaign_id, name)
    is_alias = canon_name.lower().strip() != name.lower().strip()
    return ResolveAliasResponse(
        campaign_id=campaign_id,
        input_name=name,
        canonical_name=canon_name,
        is_alias=is_alias,
    )
