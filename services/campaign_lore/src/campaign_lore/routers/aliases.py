"""Alias consolidation router for knowledge graph entities."""

from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel, Field

from campaign_lore.dependencies import (
    get_retrieval_engine,
)
from campaign_lore.retrieval import LoreRetrievalEngine

router = APIRouter(tags=["Entity Aliases"])


class ConsolidateAliasRequest(BaseModel):
    """Payload to consolidate an alias into a canonical entity node."""

    campaign_id: UUID = Field(description="Campaign UUID")
    canonical_name: str = Field(description="Canonical entity name (e.g. 'Sir Gareth')")
    alias_name: str = Field(description="Alias name or title (e.g. 'The Silver Knight')")
    reason: str = Field(default="alias consolidation", description="Rationale for consolidation")
    document_id: UUID | None = Field(default=None, description="Optional document aggregate ID")


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


@router.post("/api/v1/lore/aliases/consolidate", response_model=ConsolidateAliasResponse)
async def consolidate_alias(
    req: ConsolidateAliasRequest,
    retrieval_engine: Annotated[LoreRetrievalEngine, Depends(get_retrieval_engine)],
) -> ConsolidateAliasResponse:
    """Merge an alias title into a canonical entity node using redstring Consolidator."""
    canon_id, alias_id = await retrieval_engine.consolidate_alias(
        campaign_id=req.campaign_id,
        canonical_name=req.canonical_name,
        alias_name=req.alias_name,
        document_id=req.document_id,
        reason=req.reason,
    )

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
