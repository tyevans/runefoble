"""Document ingestion and retrieval router for Campaign Lore."""

from typing import Annotated, Any
from uuid import UUID, uuid4

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from runefoble_auth.spicedb import SpiceDBClient
from runefoble_platform.event_sourcing import AggregateRepository

from campaign_lore.aggregate import LoreDocumentAggregate, LoreDocumentState
from campaign_lore.dependencies import (
    check_user_can_read_secrets,
    get_current_user_id,
    get_repo,
    get_retrieval_engine,
    get_spicedb_client,
)
from campaign_lore.retrieval import LoreRetrievalEngine

router = APIRouter(tags=["Lore Documents"])


class IngestDocumentRequest(BaseModel):
    """Payload to ingest a worldbuilding document."""

    campaign_id: UUID = Field(description="Campaign UUID")
    title: str = Field(description="Title of lore document")
    content: str = Field(description="Markdown or text lore content")
    is_secret: bool = Field(default=False, description="Whether lore is restricted to DMs/GMs")
    author_id: str | None = Field(default=None, description="Author identifier")
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
    user_id: Annotated[str | None, Depends(get_current_user_id)],
    repo: Annotated[AggregateRepository[LoreDocumentAggregate], Depends(get_repo)],
    retrieval_engine: Annotated[LoreRetrievalEngine, Depends(get_retrieval_engine)],
    spicedb: Annotated[SpiceDBClient, Depends(get_spicedb_client)],
) -> IngestDocumentResponse:
    """Ingest a new worldbuilding document, extract knowledge graphs, and build hybrid indices."""
    # If document is marked secret, ensure user has permission or is creating it as DM/author
    doc_id = uuid4()
    aggregate = LoreDocumentAggregate(doc_id)
    aggregate.ingest(
        campaign_id=req.campaign_id,
        title=req.title,
        content=req.content,
        is_secret=req.is_secret,
        author_id=req.author_id or user_id,
        metadata={"tags": req.tags, **req.metadata},
    )
    await repo.save(aggregate)

    # Ingest into redstring graph and hybrid vector/chunk stores
    index_res = await retrieval_engine.ingest_document(
        document_id=doc_id,
        campaign_id=req.campaign_id,
        title=req.title,
        content=req.content,
        is_secret=req.is_secret,
        aliases=req.aliases,
    )

    # Find entities produced for this campaign/document to record on event stream
    ents = await retrieval_engine.graph.find_entities(req.campaign_id)
    extracted_entities = [
        {"name": e.name, "entity_type": e.entity_type, "id": str(e.id)} for e in ents
    ]
    extracted_relationships = []
    for e in ents:
        rel_items = await retrieval_engine.graph.get_relationships(e.id, req.campaign_id)
        for r in rel_items:
            extracted_relationships.append(
                {
                    "source_entity_id": str(r.source_entity_id),
                    "target_entity_id": str(r.target_entity_id),
                    "relationship_type": r.relationship_type,
                }
            )

    aggregate.record_extracted_entities(
        entities=extracted_entities,
        relationships=extracted_relationships,
    )
    await repo.save(aggregate)

    # Write SpiceDB relationship tuple for object authorization
    await spicedb.write_relationship(
        resource_type="lore_document",
        resource_id=str(doc_id),
        relation="campaign",
        subject_type="campaign",
        subject_id=str(req.campaign_id),
    )

    return IngestDocumentResponse(
        document_id=doc_id,
        campaign_id=req.campaign_id,
        title=req.title,
        is_secret=req.is_secret,
        entities_count=index_res["entities_count"],
        relationships_count=index_res["relationships_count"],
        chunks_count=index_res["chunks_count"],
        status="indexed",
    )


@router.get("/api/v1/lore/documents/{document_id}", response_model=LoreDocumentState)
async def get_document(
    document_id: UUID,
    user_id: Annotated[str | None, Depends(get_current_user_id)],
    repo: Annotated[AggregateRepository[LoreDocumentAggregate], Depends(get_repo)],
    spicedb: Annotated[SpiceDBClient, Depends(get_spicedb_client)],
) -> LoreDocumentState:
    """Retrieve an ingested lore document by UUID, enforcing SpiceDB Zanzibar access control."""
    try:
        doc = await repo.load(document_id)
    except Exception as exc:
        raise HTTPException(status_code=404, detail="Lore document not found") from exc

    # Enforce SpiceDB Zanzibar authorization for secret lore
    if doc.state.is_secret:
        can_read = await check_user_can_read_secrets(user_id, doc.state.campaign_id, spicedb)
        if not can_read:
            raise HTTPException(
                status_code=403,
                detail="Forbidden: SpiceDB Zanzibar policy denies access to DM-only secret lore.",
            )

    return doc.state
