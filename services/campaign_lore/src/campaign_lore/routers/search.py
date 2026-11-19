"""Hybrid RAG retrieval search router powered by redstring."""

import time
from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends
from pydantic import BaseModel, ConfigDict, Field
from runefoble_auth.factory import get_spicedb_client
from runefoble_auth.port import SpiceDBPort

from campaign_lore.dependencies import (
    get_retrieval_engine,
)
from campaign_lore.identity import CallerId, get_principal
from campaign_lore.permissions import (
    check_user_can_read_secrets,
)
from campaign_lore.retrieval import LoreRetrievalEngine

router = APIRouter(tags=["Lore Search & RAG"], dependencies=[Depends(get_principal)])


class LoreSearchRequest(BaseModel):
    """Payload to execute hybrid RAG search query. The caller is the verified bearer subject."""

    model_config = ConfigDict(extra="forbid")

    campaign_id: UUID = Field(description="Campaign UUID")
    query: str = Field(description="Search prompt, question, or entity query")
    limit: int = Field(default=10, ge=1, le=50, description="Max results to return")
    include_graph_walk: bool = Field(
        default=True, description="Whether to include graph neighbor traversal"
    )


class LoreSearchResultItemSchema(BaseModel):
    """Individual retrieved result matching the query."""

    text: str
    score: float
    document_id: UUID
    document_title: str
    is_secret: bool
    entities: list[str] = Field(default_factory=list)
    graph_context: list[str] = Field(default_factory=list)


class LoreSearchResponse(BaseModel):
    """Response returned from hybrid RAG search."""

    campaign_id: UUID
    query: str
    results_count: int
    took_ms: float
    can_read_secrets: bool
    results: list[LoreSearchResultItemSchema]


@router.post("/api/v1/lore/search", response_model=LoreSearchResponse)
async def search_lore(
    req: LoreSearchRequest,
    user_id: CallerId,
    retrieval_engine: Annotated[LoreRetrievalEngine, Depends(get_retrieval_engine)],
    spicedb: Annotated[SpiceDBPort, Depends(get_spicedb_client)],
) -> LoreSearchResponse:
    """Execute hybrid search combining BM25, dense embeddings, and graph neighbor walks.

    Enforces SpiceDB Zanzibar object authorization to filter out DM secret lore for players.
    """
    start_time = time.perf_counter()
    # Check whether caller has permission to view secret lore in this campaign
    can_read_secrets = await check_user_can_read_secrets(
        user_id=user_id,
        campaign_id=req.campaign_id,
        spicedb=spicedb,
    )

    items = await retrieval_engine.hybrid_search(
        campaign_id=req.campaign_id,
        query=req.query,
        can_read_secrets=can_read_secrets,
        limit=req.limit,
        include_graph_walk=req.include_graph_walk,
    )

    elapsed_ms = round((time.perf_counter() - start_time) * 1000, 2)

    schema_results = [
        LoreSearchResultItemSchema(
            text=item.text,
            score=item.score,
            document_id=item.document_id,
            document_title=item.document_title,
            is_secret=item.is_secret,
            entities=item.entities,
            graph_context=item.graph_context,
        )
        for item in items
    ]

    return LoreSearchResponse(
        campaign_id=req.campaign_id,
        query=req.query,
        results_count=len(schema_results),
        took_ms=elapsed_ms,
        can_read_secrets=can_read_secrets,
        results=schema_results,
    )
