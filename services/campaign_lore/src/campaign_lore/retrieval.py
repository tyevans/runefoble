"""Hybrid Retrieval Engine powered by redstring.

Combines graph neighbor traversal, dense vector embeddings, and BM25 lexical keyword scoring.
"""

import logging
import re
from dataclasses import dataclass, field
from datetime import UTC, datetime
from typing import Any
from uuid import UUID, uuid4

import redstring
from pydantic import BaseModel

logger = logging.getLogger(__name__)


class WorldbuildingLlmProvider:
    """Extraction provider extracting entities, relationships, and aliases from worldbuilding text."""

    def __init__(self, model: str = "runefoble/worldbuilding-ner-v1") -> None:
        self._model = model

    @property
    def model(self) -> str:
        return self._model

    async def extract[S: BaseModel](
        self,
        text: str,
        schema: type[S],
        *,
        system_prompt: str | None = None,
    ) -> S:
        """Extract structured entities and relationships from worldbuilding lore text."""
        entities: list[redstring.ExtractedEntity] = []
        relationships: list[redstring.ExtractedRelationship] = []

        # Heuristic entity detection for tabletop worldbuilding lore
        # 1. Look for explicit alias patterns: "X is also known as Y", "X, also known as Y"
        alias_patterns = [
            r"([A-Z][a-zA-Z\s]+?)\s+is\s+also\s+known\s+as\s+([A-Z][a-zA-Z\s]+?)(?:\.|\,|$)",
            r"([A-Z][a-zA-Z\s]+?)\s+known\s+as\s+([A-Z][a-zA-Z\s]+?)(?:\.|\,|$)",
            r"([A-Z][a-zA-Z\s]+?)\s+\(also\s+called\s+([A-Z][a-zA-Z\s]+?)\)",
        ]
        alias_pairs: list[tuple[str, str]] = []
        for pat in alias_patterns:
            for match in re.finditer(pat, text):
                canon = match.group(1).strip()
                alias = match.group(2).strip()
                alias_pairs.append((canon, alias))

        # 2. Extract notable capitalized proper noun phrases (NPCs, factions, locations)
        # e.g., "Sir Gareth", "The Silver Knight", "Citadel of Light", "Neverwinter"
        proper_nouns = re.findall(
            r"\b(?:The\s+)?(?:Sir\s+|Lady\s+|Lord\s+|Archmage\s+|King\s+|Queen\s+)?[A-Z][a-z]+(?:\s+(?:of\s+)?[A-Z][a-z]+)*\b",
            text,
        )

        seen_names = set()
        for name in proper_nouns:
            clean_name = name.strip()
            if len(clean_name) < 3 or clean_name in seen_names:
                continue
            seen_names.add(clean_name)

            # Heuristic entity typing
            etype = "entity"
            lower_name = clean_name.lower()
            if any(
                title in lower_name
                for title in ["sir", "lady", "lord", "knight", "king", "queen", "mage"]
            ):
                etype = "npc"
            elif any(
                loc in lower_name
                for loc in ["citadel", "keep", "forest", "castle", "city", "tower", "mount", "lake"]
            ):
                etype = "location"
            elif any(
                fac in lower_name
                for loc in ["order", "guild", "cult", "cabal", "clan", "alliance"]
                for fac in [loc]
            ):
                etype = "faction"

            entities.append(
                redstring.ExtractedEntity(
                    name=clean_name,
                    entity_type=etype,
                    description=f"{etype.upper()} mentioned in campaign lore",
                    confidence=0.9,
                )
            )

        # 3. Add explicit alias entities and relationships
        for canon, alias in alias_pairs:
            if canon not in seen_names:
                entities.append(
                    redstring.ExtractedEntity(name=canon, entity_type="npc", confidence=0.95)
                )
                seen_names.add(canon)
            if alias not in seen_names:
                entities.append(
                    redstring.ExtractedEntity(name=alias, entity_type="npc", confidence=0.95)
                )
                seen_names.add(alias)
            relationships.append(
                redstring.ExtractedRelationship(
                    source_name=canon,
                    target_name=alias,
                    relationship_type="alias_of",
                    confidence=0.99,
                )
            )

        # 4. Extract relational connections: "X guards Y", "X rules Y", "X located in Y"
        rel_pattern = r"([A-Z][a-zA-Z\s]+?)\s+(guards|rules|located in|allied with|serves)\s+([A-Z][a-zA-Z\s]+?)(?:\.|\,|$)"
        for match in re.finditer(rel_pattern, text):
            src = match.group(1).strip()
            rel = match.group(2).strip()
            tgt = match.group(3).strip()
            relationships.append(
                redstring.ExtractedRelationship(
                    source_name=src,
                    target_name=tgt,
                    relationship_type=rel,
                    confidence=0.85,
                )
            )

        return schema.model_validate({"entities": entities, "relationships": relationships})


@dataclass
class DocumentMetadata:
    """Tracked metadata for ingested documents."""

    document_id: UUID
    campaign_id: UUID
    title: str
    content: str
    is_secret: bool
    created_at: datetime = field(default_factory=lambda: datetime.now(UTC))


@dataclass
class LoreSearchResultItem:
    """Individual item returned from hybrid search."""

    text: str
    score: float
    document_id: UUID
    document_title: str
    is_secret: bool
    entities: list[str] = field(default_factory=list)
    graph_context: list[str] = field(default_factory=list)


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
            embeddings=self.embeddings,
            chunks=self.chunks,
        )
        self.entity_retriever = redstring.Retriever(
            embeddings=self.embeddings,
            vectors=self.vectors,
            graph=self.graph,
        )
        # Fast document metadata index: document_id -> DocumentMetadata
        self._documents: dict[UUID, DocumentMetadata] = {}

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
        # Record document metadata
        meta = DocumentMetadata(
            document_id=document_id,
            campaign_id=campaign_id,
            title=title,
            content=content,
            is_secret=is_secret,
        )
        self._documents[document_id] = meta

        source_doc = redstring.SourceDocument(
            id=str(document_id),
            title=title,
            text=content,
        )

        report = await redstring.build_graph(
            source_doc,
            provider=self.llm_provider,
            store=self.graph,
            tenant_id=campaign_id,
            embedding_provider=self.embeddings,
            vector_store=self.vectors,
            chunks=self.chunks,
        )

        # Handle explicit aliases if provided
        if aliases:
            for alias_name, canonical_name in aliases.items():
                await self.consolidate_alias(
                    campaign_id=campaign_id,
                    canonical_name=canonical_name,
                    alias_name=alias_name,
                    document_id=document_id,
                )

        return {
            "document_id": document_id,
            "campaign_id": campaign_id,
            "title": title,
            "is_secret": is_secret,
            "entities_count": report.entities,
            "relationships_count": report.relationships,
            "chunks_count": report.chunks_written,
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
        # Find or create canonical entity
        canon_entities = await self.graph.find_entities(
            campaign_id, name=canonical_name.lower().strip()
        )
        now = datetime.now(UTC)
        prov = redstring.Provenance(
            observed_at=now,
            extraction_method=redstring.ExtractionMethod.LLM,
            confidence=1.0,
            source_id=str(document_id or uuid4()),
        )
        if canon_entities:
            canonical_entity = canon_entities[0]
            canon_id = canonical_entity.id
        else:
            canon_id = uuid4()
            canonical_entity = redstring.Entity(
                id=canon_id,
                tenant_id=campaign_id,
                name=canonical_name,
                normalized_name=canonical_name.lower().strip(),
                entity_type="npc",
                provenance=prov,
            )
            await self.graph.upsert_entity(canonical_entity)

        # Find or create alias entity
        alias_entities = await self.graph.find_entities(
            campaign_id, name=alias_name.lower().strip()
        )
        alias_ids = [e.id for e in alias_entities]
        if not alias_ids:
            alias_id = uuid4()
            alias_entity = redstring.Entity(
                id=alias_id,
                tenant_id=campaign_id,
                name=alias_name,
                normalized_name=alias_name.lower().strip(),
                entity_type="npc",
                provenance=prov,
            )
            await self.graph.upsert_entity(alias_entity)
            alias_ids = [alias_id]
        else:
            alias_id = alias_ids[0]

        # Merge via Consolidator
        await self.consolidator.merge(
            tenant_id=campaign_id,
            canonical_entity_id=canon_id,
            merged_entity_ids=alias_ids,
            merge_reason=reason,
        )

        return canon_id, alias_id

    async def resolve_alias(self, campaign_id: UUID, alias_name: str) -> str:
        """Resolve a possible alias name to its canonical entity name."""
        entities = await self.graph.find_entities(campaign_id, name=alias_name.lower().strip())
        if not entities:
            all_ents = await self.graph.find_entities(campaign_id)
            for ent in all_ents:
                if ent.normalized_name == alias_name.lower().strip():
                    entities = [ent]
                    break

        if not entities:
            return alias_name

        for ent in entities:
            resolved_map = await self.graph.resolve_entity_ids([ent.id], campaign_id)
            canon_id = resolved_map.get(ent.id, ent.id)
            if canon_id != ent.id:
                canon_entity = await self.graph.get_entity(canon_id, campaign_id)
                if canon_entity:
                    return canon_entity.name

        return alias_name

    async def hybrid_search(
        self,
        campaign_id: UUID,
        query: str,
        can_read_secrets: bool = False,
        limit: int = 10,
        include_graph_walk: bool = True,
    ) -> list[LoreSearchResultItem]:
        """Execute hybrid search combining BM25, dense embeddings, and graph neighbor walks.

        Filters out secret DM lore if can_read_secrets is False.
        """
        # 1. Resolve any query aliases first (e.g. "The Silver Knight" -> "Sir Gareth")
        resolved_query_entity = await self.resolve_alias(campaign_id, query)
        effective_query = (
            f"{query} {resolved_query_entity}".strip() if resolved_query_entity != query else query
        )

        # 2. Retrieve ranked chunks (semantic vectors + BM25)
        chunk_results = await self.chunk_retriever.retrieve_chunks(
            effective_query,
            tenant_id=campaign_id,
            k=limit * 2,
        )

        # 3. Retrieve ranked entities (semantic vectors + lexical)
        entity_results = await self.entity_retriever.retrieve(
            effective_query,
            tenant_id=campaign_id,
            k=limit,
        )

        # Collect entities matched and their graph neighbor walks
        graph_context: dict[UUID, list[str]] = {}
        if include_graph_walk:
            matched_entity_ids = [m.entity.id for m in entity_results.matches]
            # Also resolve any merged alias entity ids
            if matched_entity_ids:
                resolved_map = await self.graph.resolve_entity_ids(matched_entity_ids, campaign_id)
                canonical_ids = list(set(resolved_map.values()))

                for e_id in canonical_ids:
                    rel_items = await self.graph.get_relationships_for([e_id], campaign_id)
                    contexts = []
                    for r in rel_items:
                        src_ent = await self.graph.get_entity(r.source_entity_id, campaign_id)
                        tgt_ent = await self.graph.get_entity(r.target_entity_id, campaign_id)
                        src_name = src_ent.name if src_ent else str(r.source_entity_id)
                        tgt_name = tgt_ent.name if tgt_ent else str(r.target_entity_id)
                        contexts.append(f"{src_name} --[{r.relationship_type}]--> {tgt_name}")
                    if contexts:
                        graph_context[e_id] = contexts

        # 4. Assemble and filter results based on secret authorization
        items: list[LoreSearchResultItem] = []
        for scored_chunk in chunk_results.matches:
            c = scored_chunk.chunk
            try:
                doc_id = UUID(c.source_id)
            except (ValueError, TypeError):
                continue

            doc_meta = self._documents.get(doc_id)
            if not doc_meta:
                continue

            # Authorization filter: omit secret lore if caller is not authorized
            if doc_meta.is_secret and not can_read_secrets:
                continue

            # Extract entity names from chunk
            entity_names = []
            chunk_graph_info: list[str] = []
            for eid in c.entity_ids:
                ent = await self.graph.get_entity(eid, campaign_id)
                if ent:
                    entity_names.append(ent.name)
                if eid in graph_context:
                    chunk_graph_info.extend(graph_context[eid])

            items.append(
                LoreSearchResultItem(
                    text=c.text,
                    score=float(scored_chunk.score),
                    document_id=doc_id,
                    document_title=doc_meta.title,
                    is_secret=doc_meta.is_secret,
                    entities=entity_names,
                    graph_context=chunk_graph_info,
                )
            )

            if len(items) >= limit:
                break

        return items

    def get_document(self, document_id: UUID) -> DocumentMetadata | None:
        """Retrieve document metadata by UUID."""
        return self._documents.get(document_id)
