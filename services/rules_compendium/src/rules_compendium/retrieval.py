"""Hybrid BM25 and Semantic retrieval engine for rules compendium powered by redstring."""

import logging
import time
from typing import Any
from uuid import UUID

import redstring

from rules_compendium.models import RuleSearchResultItem
from rules_compendium.srd_data import (
    CANONICAL_CONDITIONS,
    CANONICAL_MONSTERS,
    CANONICAL_SPELLS,
)

logger = logging.getLogger(__name__)

CANONICAL_TENANT_ID = UUID("00000000-0000-0000-0000-000000000001")


class CompendiumRetrievalEngine:
    """Hybrid BM25 and semantic vector search engine over canonical SRD and homebrew rules."""

    def __init__(self) -> None:
        self.embeddings = redstring.FakeEmbeddingProvider()
        dim = self.embeddings.dimension
        self.chunks = redstring.InMemoryChunkStore(dimension=dim)
        self.chunk_retriever = redstring.ChunkRetriever(
            embeddings=self.embeddings,
            chunks=self.chunks,
        )

        # Fast direct lookups
        self._monsters: dict[str, dict[str, Any]] = {}
        self._spells: dict[str, dict[str, Any]] = {}
        self._conditions: dict[str, dict[str, Any]] = {}
        self._homebrew: dict[UUID, list[dict[str, Any]]] = {}

        self._initialized = False

    async def initialize_srd_data(self) -> None:
        """Pre-index canonical SRD monsters, spells, and conditions."""
        if self._initialized:
            return

        stored_chunks: list[redstring.StoredChunk] = []

        # Index monsters
        for m in CANONICAL_MONSTERS:
            name_lower = m["name"].lower()
            self._monsters[name_lower] = m
            traits_str = " ".join(t.get("description", "") for t in m.get("traits", []))
            actions_str = " ".join(a.get("description", "") for a in m.get("actions", []))
            text = (
                f"{m['name']} ({m.get('size', 'Medium')} {m.get('creature_type', '')}, "
                f"CR {m.get('challenge_rating', '')}, {m.get('xp', '')} XP, role: {m.get('role', 'brute')}): "
                f"AC {m.get('armor_class', '')}, HP {m.get('hit_points', '')}, speed {m.get('speed', '')}. "
                f"{m.get('description', '')} Traits: {traits_str} Actions: {actions_str}"
            )
            embs = await self.embeddings.embed([text])
            stored_chunks.append(
                redstring.StoredChunk(
                    tenant_id=CANONICAL_TENANT_ID,
                    source_id=f"srd-monster-{name_lower}",
                    text=text,
                    chunk_index=0,
                    start_char=0,
                    end_char=len(text),
                    entity_ids=[],
                    metadata={
                        "category": "monster",
                        "name": m["name"],
                        "details": m,
                        "is_homebrew": False,
                        "campaign_id": None,
                    },
                    embedding=embs[0],
                )
            )

        # Index spells
        for s in CANONICAL_SPELLS:
            name_lower = s["name"].lower()
            self._spells[name_lower] = s
            text = (
                f"{s['name']} (Level {s.get('level', '')} {s.get('school', '')} spell): "
                f"Casting time: {s.get('casting_time', '')}, Range: {s.get('range', '')}, "
                f"Components: {s.get('components', '')}, Duration: {s.get('duration', '')}. "
                f"{s.get('description', '')}"
            )
            embs = await self.embeddings.embed([text])
            stored_chunks.append(
                redstring.StoredChunk(
                    tenant_id=CANONICAL_TENANT_ID,
                    source_id=f"srd-spell-{name_lower}",
                    text=text,
                    chunk_index=0,
                    start_char=0,
                    end_char=len(text),
                    entity_ids=[],
                    metadata={
                        "category": "spell",
                        "name": s["name"],
                        "details": s,
                        "is_homebrew": False,
                        "campaign_id": None,
                    },
                    embedding=embs[0],
                )
            )

        # Index conditions
        for c in CANONICAL_CONDITIONS:
            name_lower = c["name"].lower()
            self._conditions[name_lower] = c
            effects_str = " ".join(c.get("effects", []))
            text = f"{c['name']} (Condition): {c.get('description', '')} Effects: {effects_str}"
            embs = await self.embeddings.embed([text])
            stored_chunks.append(
                redstring.StoredChunk(
                    tenant_id=CANONICAL_TENANT_ID,
                    source_id=f"srd-condition-{name_lower}",
                    text=text,
                    chunk_index=0,
                    start_char=0,
                    end_char=len(text),
                    entity_ids=[],
                    metadata={
                        "category": "condition",
                        "name": c["name"],
                        "details": c,
                        "is_homebrew": False,
                        "campaign_id": None,
                    },
                    embedding=embs[0],
                )
            )

        await self.chunks.upsert_many(stored_chunks)
        self._initialized = True

    async def index_homebrew_rule(
        self,
        rule_id: UUID,
        campaign_id: UUID,
        author_id: str,
        rule_type: str,
        title: str,
        content: dict[str, Any],
    ) -> None:
        """Index a custom homebrew monster or rule into campaign-isolated redstring storage."""
        entry = {
            "rule_id": str(rule_id),
            "campaign_id": str(campaign_id),
            "author_id": author_id,
            "rule_type": rule_type,
            "title": title,
            "content": content,
            "is_homebrew": True,
        }
        if campaign_id not in self._homebrew:
            self._homebrew[campaign_id] = []
        self._homebrew[campaign_id].append(entry)

        # If it's a monster, store in monster lookup if tied to campaign
        if rule_type.lower() == "monster":
            m_data = {
                "monster_id": str(rule_id),
                "name": title,
                "challenge_rating": float(content.get("challenge_rating", 1.0)),
                "creature_type": content.get("creature_type", "homebrew"),
                "size": content.get("size", "Medium"),
                "armor_class": int(content.get("armor_class", 10)),
                "hit_points": int(content.get("hit_points", 10)),
                "speed": content.get("speed", "30 ft."),
                "xp": int(content.get("xp", 100)),
                "role": content.get("role", "brute"),
                "stats": content.get("stats", {}),
                "description": content.get("description", ""),
                "is_homebrew": True,
                "campaign_id": campaign_id,
            }
            self._monsters[title.lower()] = m_data

        content_str = " ".join(
            f"{k}: {v}" for k, v in content.items() if isinstance(v, (str, int, float))
        )
        text = f"{title} (Homebrew {rule_type}): {content_str}"
        embs = await self.embeddings.embed([text])
        chunk = redstring.StoredChunk(
            tenant_id=campaign_id,
            source_id=f"homebrew-{rule_id}",
            text=text,
            chunk_index=0,
            start_char=0,
            end_char=len(text),
            entity_ids=[],
            metadata={
                "category": "homebrew",
                "name": title,
                "rule_type": rule_type,
                "details": content,
                "is_homebrew": True,
                "campaign_id": str(campaign_id),
            },
            embedding=embs[0],
        )
        await self.chunks.upsert_many([chunk])

    async def hybrid_search(
        self,
        query: str,
        category: str | None = None,
        campaign_id: UUID | None = None,
        can_view_homebrew: bool = False,
        limit: int = 10,
    ) -> tuple[list[RuleSearchResultItem], float]:
        """Perform hybrid BM25 and semantic vector lookup across SRD and authorized homebrew rules."""
        if not self._initialized:
            await self.initialize_srd_data()

        t0 = time.perf_counter()

        # 1. Search canonical SRD rules
        srd_res = await self.chunk_retriever.retrieve_chunks(
            query,
            tenant_id=CANONICAL_TENANT_ID,
            k=limit * 2,
        )

        all_matches = list(srd_res.matches)

        # 2. Search campaign homebrew if authorized and campaign_id provided
        if campaign_id and can_view_homebrew:
            hb_res = await self.chunk_retriever.retrieve_chunks(
                query,
                tenant_id=campaign_id,
                k=limit * 2,
            )
            all_matches.extend(hb_res.matches)

        # Sort matches by score descending
        all_matches.sort(key=lambda m: float(m.score), reverse=True)

        results: list[RuleSearchResultItem] = []
        seen_names = set()

        for scored_chunk in all_matches:
            c = scored_chunk.chunk
            meta = c.metadata or {}
            item_cat = meta.get("category", "rule")
            item_name = meta.get("name", "Unknown")

            if category and item_cat.lower() != category.lower():
                continue

            if item_name in seen_names:
                continue
            seen_names.add(item_name)

            results.append(
                RuleSearchResultItem(
                    category=item_cat,
                    name=item_name,
                    score=float(scored_chunk.score),
                    summary=c.text[:200] + ("..." if len(c.text) > 200 else ""),
                    details=meta.get("details", {}),
                    is_homebrew=meta.get("is_homebrew", False),
                    campaign_id=UUID(meta["campaign_id"]) if meta.get("campaign_id") else None,
                )
            )

            if len(results) >= limit:
                break

        took_ms = (time.perf_counter() - t0) * 1000
        return results, took_ms

    def get_monster(self, name: str) -> dict[str, Any] | None:
        """Find monster by name (case-insensitive)."""
        return self._monsters.get(name.lower().strip())

    def get_spell(self, name: str) -> dict[str, Any] | None:
        """Find spell by name (case-insensitive)."""
        return self._spells.get(name.lower().strip())

    def get_condition(self, name: str) -> dict[str, Any] | None:
        """Find condition by name (case-insensitive)."""
        return self._conditions.get(name.lower().strip())

    def get_homebrew_by_campaign(self, campaign_id: UUID) -> list[dict[str, Any]]:
        """Retrieve homebrew rules belonging to a specific campaign."""
        return self._homebrew.get(campaign_id, [])
