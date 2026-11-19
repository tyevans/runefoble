"""Document ingestion and retrieval router for Campaign Lore."""

from typing import Annotated, Any
from uuid import UUID, uuid4

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, ConfigDict, Field
from runefoble_auth.errors import AuthzError
from runefoble_auth.factory import get_spicedb_client
from runefoble_auth.port import SpiceDBPort
from runefoble_platform.aggregate_loading import load_if_exists
from runefoble_platform.errors import ServiceUnavailableError
from runefoble_platform.event_sourcing import AggregateRepository

from campaign_lore.aggregate import LoreDocumentAggregate, LoreDocumentState
from campaign_lore.dependencies import (
    get_repo,
    get_retrieval_engine,
)
from campaign_lore.identity import CallerId, get_principal
from campaign_lore.permissions import (
    check_user_can_read_secrets,
    check_user_can_run_session,
    check_user_can_view_campaign,
)
from campaign_lore.retrieval import LoreRetrievalEngine

router = APIRouter(tags=["Lore Documents"], dependencies=[Depends(get_principal)])


class IngestDocumentRequest(BaseModel):
    """Payload to ingest a worldbuilding document. The author is the verified caller."""

    model_config = ConfigDict(extra="forbid")

    campaign_id: UUID = Field(description="Campaign UUID")
    title: str = Field(description="Title of lore document")
    content: str = Field(description="Markdown or text lore content")
    is_secret: bool = Field(default=False, description="Whether lore is restricted to DMs/GMs")
    tags: list[str] = Field(default_factory=list, description="Categorization tags")
    aliases: dict[str, str] | None = Field(
        default=None, description="Optional map of alias -> canonical entity name"
    )
    metadata: dict[str, Any] = Field(default_factory=dict, description="Arbitrary attributes")


class IngestDocumentResponse(BaseModel):
    """Response returned upon document ingestion."""

    document_id: UUID
    campaign_id: UUID
    title: str
    is_secret: bool
    entities_count: int
    relationships_count: int
    chunks_count: int
    status: str = "indexed"


@router.post("/api/v1/lore/documents", response_model=IngestDocumentResponse)
async def ingest_document(
    req: IngestDocumentRequest,
    user_id: CallerId,
    repo: Annotated[AggregateRepository[LoreDocumentAggregate], Depends(get_repo)],
    retrieval_engine: Annotated[LoreRetrievalEngine, Depends(get_retrieval_engine)],
    spicedb: Annotated[SpiceDBPort, Depends(get_spicedb_client)],
) -> IngestDocumentResponse:
    """Ingest a new worldbuilding document, extract knowledge graphs, and build hybrid indices."""
    if not await check_user_can_run_session(user_id, req.campaign_id, spicedb):
        raise HTTPException(
            status_code=403,
            detail="Forbidden: Only campaign run_session members can ingest lore documents.",
        )
    doc_id = uuid4()
    aggregate = LoreDocumentAggregate(doc_id)
    aggregate.ingest(
        campaign_id=req.campaign_id,
        title=req.title,
        content=req.content,
        is_secret=req.is_secret,
        author_id=user_id,
        metadata={"tags": req.tags, **req.metadata},
    )
    # The authorization tuple is written before the document is saved. A failed write
    # returns 503 and the document is not saved.
    try:
        await spicedb.write_relationship(
            resource_type="lore_document",
            resource_id=str(doc_id),
            relation="campaign",
            subject_type="campaign",
            subject_id=str(req.campaign_id),
        )
    except AuthzError as exc:
        raise ServiceUnavailableError(
            "Lore authorization is unavailable. The document was not saved."
        ) from exc
    await repo.save(aggregate)

    # Index into the redstring graph and hybrid vector/chunk stores
    summary = await retrieval_engine.ingest_document(
        document_id=doc_id,
        campaign_id=req.campaign_id,
        title=req.title,
        content=req.content,
        is_secret=req.is_secret,
    )
    for alias_name, canonical_name in (req.aliases or {}).items():
        canon_id, alias_id = await retrieval_engine.consolidate_alias(
            campaign_id=req.campaign_id,
            canonical_name=canonical_name,
            alias_name=alias_name,
            document_id=doc_id,
        )
        aggregate.consolidate_alias(
            canonical_entity_id=canon_id,
            canonical_name=canonical_name,
            alias_entity_id=alias_id,
            alias_name=alias_name,
        )

    aggregate.record_extracted_entities(
        entities=[
            {
                "name": e.name,
                "entity_type": e.entity_type,
                "id": str(e.id),
                "extraction_method": e.provenance.extraction_method.value,
            }
            for e in summary.entities
        ],
        relationships=[
            {
                "source_entity_id": str(r.source_entity_id),
                "target_entity_id": str(r.target_entity_id),
                "relationship_type": r.relationship_type,
            }
            for r in summary.relationships
        ],
    )
    await repo.save(aggregate)

    return IngestDocumentResponse(
        document_id=doc_id,
        campaign_id=req.campaign_id,
        title=req.title,
        is_secret=req.is_secret,
        entities_count=len(summary.entities),
        relationships_count=len(summary.relationships),
        chunks_count=summary.chunks_written,
        status="indexed",
    )


@router.get("/api/v1/lore/documents/{document_id}", response_model=LoreDocumentState)
async def get_document(
    document_id: UUID,
    user_id: CallerId,
    repo: Annotated[AggregateRepository[LoreDocumentAggregate], Depends(get_repo)],
    spicedb: Annotated[SpiceDBPort, Depends(get_spicedb_client)],
) -> LoreDocumentState:
    """Retrieve an ingested lore document by UUID, enforcing SpiceDB Zanzibar access control."""
    doc = await load_if_exists(repo, document_id)
    if doc is None:
        raise HTTPException(status_code=404, detail="Lore document not found")

    if doc.state.is_secret:
        # Secret lore needs run_session (lore_document.read_secret).
        can_read = await check_user_can_read_secrets(user_id, doc.state.campaign_id, spicedb)
        if not can_read:
            raise HTTPException(
                status_code=403,
                detail="Forbidden: SpiceDB Zanzibar policy denies access to DM-only secret lore.",
            )
    else:
        # Public lore needs campaign view (lore_document.read_public).
        can_view = await check_user_can_view_campaign(user_id, doc.state.campaign_id, spicedb)
        if not can_view:
            raise HTTPException(
                status_code=403,
                detail="Forbidden: User lacks campaign view permission for this lore document.",
            )

    return doc.state
