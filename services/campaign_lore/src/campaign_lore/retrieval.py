"""Hybrid Retrieval Engine coordinator for campaign lore, powered by redstring.

Combines graph neighbor traversal, dense vector embeddings, and BM25 lexical keyword scoring.
The engine receives its ports from the composition root (see retrieval_factory.py).
"""

import logging
from collections.abc import Sequence
from dataclasses import dataclass
from datetime import UTC, datetime
from uuid import UUID

import redstring

from campaign_lore.extraction import get_or_create_entity
from campaign_lore.models import DocumentMetadata, LoreSearchResultItem
from campaign_lore.pattern_graph import build_pattern_graph

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class IngestSummary:
    """What one document contributed to the graph and the chunk corpus."""

    entities: list[redstring.Entity]
    relationships: list[redstring.Relationship]
    chunks_written: int


class LoreRetrievalEngine:
    """Manages knowledge graph construction, alias consolidation, and hybrid search via redstring."""

    def __init__(
        self,
        *,
        embeddings: redstring.EmbeddingProvider,
        graph: redstring.GraphStore,
        vectors: redstring.VectorStore,
        chunks: redstring.ChunkStore,
    ) -> None:
        self.embeddings = embeddings
        self.graph = graph
        self.vectors = vectors
        self.chunks = chunks
        self.consolidator = redstring.Consolidator(store=graph)
        self.chunk_retriever = redstring.ChunkRetriever(embeddings=embeddings, chunks=chunks)
        self.entity_retriever = redstring.Retriever(
            embeddings=embeddings, vectors=vectors, graph=graph
        )
        self._documents: dict[UUID, DocumentMetadata] = {}

    async def _traverse_graph(self, entity_ids: Sequence[UUID], cid: UUID) -> dict[UUID, list[str]]:
        if not entity_ids:
            return {}
        cids = set((await self.graph.resolve_entity_ids(entity_ids, cid)).values())
        ctx_map: dict[UUID, list[str]] = {}
        for eid in cids:
            ctxs = []
            for r in await self.graph.get_relationships_for([eid], cid):
                s = await self.graph.get_entity(r.source_entity_id, cid)
                t = await self.graph.get_entity(r.target_entity_id, cid)
                sn, tn = (
                    s.name if s else str(r.source_entity_id),
                    t.name if t else str(r.target_entity_id),
                )
                ctxs.append(f"{sn} --[{r.relationship_type}]--> {tn}")
            if ctxs:
                ctx_map[eid] = ctxs
        return ctx_map

    async def ingest_document(
        self,
        document_id: UUID,
        campaign_id: UUID,
        title: str,
        content: str,
        is_secret: bool = False,
    ) -> IngestSummary:
        """Index a worldbuilding document: pattern extraction, graph write, chunks, and vectors."""
        self._documents[document_id] = DocumentMetadata(
            document_id, campaign_id, title, content, is_secret
        )
        source_id = str(document_id)
        records = build_pattern_graph(campaign_id, document_id, content, datetime.now(UTC))
        entity_list = records.entities
        relationships = records.relationships
        await self.graph.upsert_entities(entity_list)
        await self.graph.upsert_relationships(relationships)

        report = await redstring.index_documents(
            [redstring.SourceDocument(id=source_id, title=title, text=content)],
            store=self.chunks,
            tenant_id=campaign_id,
            embeddings=self.embeddings,
        )
        await self._link_chunks_to_entities(campaign_id, source_id, entity_list)

        if entity_list:
            vectors = await self.embeddings.embed([e.name for e in entity_list])
            for ent, vector in zip(entity_list, vectors, strict=True):
                await self.vectors.upsert(ent.id, vector, campaign_id)

        return IngestSummary(
            entities=entity_list,
            relationships=relationships,
            chunks_written=report.chunks_written,
        )

    async def _link_chunks_to_entities(
        self, campaign_id: UUID, source_id: str, entities: list[redstring.Entity]
    ) -> None:
        """Record on each passage the entities whose names occur in it."""
        passages = await self.chunks.get_by_source(source_id, campaign_id)
        if not passages:
            return
        linked = [
            p.model_copy(update={"entity_ids": [e.id for e in entities if e.name in p.text]})
            for p in passages
        ]
        await self.chunks.upsert_many(linked)

    async def consolidate_alias(
        self,
        campaign_id: UUID,
        canonical_name: str,
        alias_name: str,
        document_id: UUID,
        reason: str = "alias consolidation",
    ) -> tuple[UUID, UUID]:
        """Consolidate an alias entity into a canonical entity (explicit, user-declared)."""
        prov = redstring.Provenance(
            observed_at=datetime.now(UTC),
            extraction_method=redstring.ExtractionMethod.MANUAL,
            confidence=1.0,
            source_id=str(document_id),
        )
        c_id = await get_or_create_entity(
            self.graph, campaign_id, canonical_name, str(document_id), prov
        )
        a_id = await get_or_create_entity(
            self.graph, campaign_id, alias_name, str(document_id), prov
        )
        await self.consolidator.merge(
            tenant_id=campaign_id,
            canonical_entity_id=c_id,
            merged_entity_ids=[a_id],
            merge_reason=reason,
        )
        return c_id, a_id

    async def resolve_alias(self, campaign_id: UUID, alias_name: str) -> str:
        """Resolve a possible alias name to its canonical entity name."""
        norm = alias_name.lower().strip()
        ents = await self.graph.find_entities(campaign_id, name=norm)
        ents = ents or [
            e for e in await self.graph.find_entities(campaign_id) if e.normalized_name == norm
        ]
        for ent in ents:
            cid = (await self.graph.resolve_entity_ids([ent.id], campaign_id)).get(ent.id, ent.id)
            if cid != ent.id and (canon := await self.graph.get_entity(cid, campaign_id)):
                return canon.name
        return alias_name

    async def hybrid_search(
        self,
        campaign_id: UUID,
        query: str,
        can_read_secrets: bool = False,
        limit: int = 10,
        include_graph_walk: bool = True,
    ) -> list[LoreSearchResultItem]:
        """Execute hybrid search combining BM25, dense embeddings, and graph neighbor walks."""
        resolved = await self.resolve_alias(campaign_id, query)
        q = f"{query} {resolved}".strip() if resolved != query else query
        chunk_res = await self.chunk_retriever.retrieve_chunks(
            q, tenant_id=campaign_id, k=limit * 2
        )
        ent_res = await self.entity_retriever.retrieve(q, tenant_id=campaign_id, k=limit)
        graph_ctx = {}
        if include_graph_walk and ent_res.matches:
            graph_ctx = await self._traverse_graph(
                [m.entity.id for m in ent_res.matches], campaign_id
            )

        items: list[LoreSearchResultItem] = []
        for sc in chunk_res.matches:
            try:
                doc_id = UUID(sc.chunk.source_id)
            except (ValueError, TypeError):
                continue
            if not (meta := self._documents.get(doc_id)) or (
                meta.is_secret and not can_read_secrets
            ):
                continue
            e_names = [
                e.name
                for eid in sc.chunk.entity_ids
                if (e := await self.graph.get_entity(eid, campaign_id))
            ]
            c_graph = [c for eid in sc.chunk.entity_ids for c in graph_ctx.get(eid, [])]
            items.append(
                LoreSearchResultItem(
                    text=sc.chunk.text,
                    score=float(sc.score),
                    document_id=doc_id,
                    document_title=meta.title,
                    is_secret=meta.is_secret,
                    entities=e_names,
                    graph_context=c_graph,
                )
            )
            if len(items) >= limit:
                break
        return items

    async def close(self) -> None:
        """Release the stores that hold connections or pools."""
        await self.vectors.close()

    def get_document(self, document_id: UUID) -> DocumentMetadata | None:
        """Retrieve document metadata by UUID."""
        return self._documents.get(document_id)


__all__ = [
    "IngestSummary",
    "LoreRetrievalEngine",
]
