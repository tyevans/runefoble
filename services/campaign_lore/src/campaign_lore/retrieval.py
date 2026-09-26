"""Hybrid Retrieval Engine coordinator powered by redstring.

Combines graph neighbor traversal, dense vector embeddings, and BM25 lexical keyword scoring.
"""

import logging
from collections.abc import Sequence
from datetime import UTC, datetime
from typing import Any
from uuid import UUID, uuid4

import redstring

from campaign_lore.extraction import WorldbuildingLlmProvider, get_or_create_entity
from campaign_lore.models import DocumentMetadata, LoreSearchResultItem
from campaign_lore.scoring import (
    bm25_score,
    cosine_similarity,
    reciprocal_rank_fusion,
    tokenize,
)

logger = logging.getLogger(__name__)


class LoreRetrievalEngine:
    """Manages knowledge graph construction, alias consolidation, and hybrid search via redstring."""

    def __init__(self) -> None:
        self.embeddings = redstring.FakeEmbeddingProvider()
        dim = self.embeddings.dimension
        self.graph = redstring.InMemoryGraphStore()
        self.vectors = redstring.InMemoryVectorStore(dimension=dim)
        self.chunks = redstring.InMemoryChunkStore(dimension=dim)
        self.consolidator = redstring.Consolidator(store=self.graph)
        self.llm_provider = WorldbuildingLlmProvider()
        self.chunk_retriever = redstring.ChunkRetriever(
            embeddings=self.embeddings, chunks=self.chunks
        )
        self.entity_retriever = redstring.Retriever(
            embeddings=self.embeddings, vectors=self.vectors, graph=self.graph
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
        aliases: dict[str, str] | None = None,
    ) -> dict[str, Any]:
        """Ingest a worldbuilding document into redstring graph and hybrid vector/BM25 chunks."""
        self._documents[document_id] = DocumentMetadata(
            document_id, campaign_id, title, content, is_secret
        )
        rep = await redstring.build_graph(
            redstring.SourceDocument(id=str(document_id), title=title, text=content),
            provider=self.llm_provider,
            store=self.graph,
            tenant_id=campaign_id,
            embedding_provider=self.embeddings,
            vector_store=self.vectors,
            chunks=self.chunks,
        )
        for a, c in (aliases or {}).items():
            await self.consolidate_alias(campaign_id, c, a, document_id=document_id)
        return {
            "document_id": document_id,
            "campaign_id": campaign_id,
            "title": title,
            "is_secret": is_secret,
            "entities_count": rep.entities,
            "relationships_count": rep.relationships,
            "chunks_count": rep.chunks_written,
        }

    async def consolidate_alias(
        self,
        campaign_id: UUID,
        canonical_name: str,
        alias_name: str,
        document_id: UUID | None = None,
        reason: str = "alias consolidation",
    ) -> tuple[UUID, UUID]:
        """Consolidate an alias entity into a canonical entity."""
        prov = redstring.Provenance(
            observed_at=datetime.now(UTC),
            extraction_method=redstring.ExtractionMethod.LLM,
            confidence=1.0,
            source_id=str(document_id or uuid4()),
        )
        c_id = await get_or_create_entity(self.graph, campaign_id, canonical_name, prov)
        a_id = await get_or_create_entity(self.graph, campaign_id, alias_name, prov)
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

    def get_document(self, document_id: UUID) -> DocumentMetadata | None:
        """Retrieve document metadata by UUID."""
        return self._documents.get(document_id)


# Backward-compatibility alias as defined in architecture records
HybridLoreEngine = LoreRetrievalEngine

__all__ = [
    "DocumentMetadata",
    "HybridLoreEngine",
    "LoreRetrievalEngine",
    "LoreSearchResultItem",
    "WorldbuildingLlmProvider",
    "bm25_score",
    "cosine_similarity",
    "reciprocal_rank_fusion",
    "tokenize",
]
