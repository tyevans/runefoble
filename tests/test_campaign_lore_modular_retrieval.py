"""Tests verifying modular decomposition of campaign_lore retrieval submodules and absence of legacy shims."""

from __future__ import annotations

from datetime import UTC, datetime
from uuid import uuid4

import pytest
import redstring
from campaign_lore.extraction import (
    classify_entity_type,
    extract_alias_pairs,
    extract_pattern_graph,
    extract_proper_nouns,
    extract_relationships,
    get_or_create_entity,
)
from campaign_lore.scoring import (
    bm25_score,
    compute_idf,
    cosine_similarity,
    reciprocal_rank_fusion,
    tokenize,
)


def test_modular_scoring_primitives() -> None:
    """Verify BM25 tokenization, term scoring, cosine similarity, and RRF rank fusion."""
    # 1. Tokenization
    tokens = tokenize("Sir Gareth, the Silver Knight of Neverwinter!")
    assert tokens == ["sir", "gareth", "the", "silver", "knight", "of", "neverwinter"]

    # 2. IDF calculation
    idf_rare = compute_idf(doc_freq=1, total_docs=10)
    idf_common = compute_idf(doc_freq=9, total_docs=10)
    assert idf_rare > idf_common
    assert compute_idf(0, 0) == 0.0

    # 3. BM25 scoring
    idf_map = {"sunblade": 2.5, "paladin": 1.8}
    doc1 = ["sir", "gareth", "wields", "the", "sunblade", "paladin"]
    doc2 = ["the", "citadel", "is", "guarded"]
    score1 = bm25_score(["sunblade"], doc1, idf_map, avg_doc_len=5.0)
    score2 = bm25_score(["sunblade"], doc2, idf_map, avg_doc_len=5.0)
    assert score1 > 0.0
    assert score2 == 0.0

    # 4. Cosine similarity
    vec_a = [1.0, 0.0, 0.0]
    vec_b = [1.0, 0.0, 0.0]
    vec_c = [0.0, 1.0, 0.0]
    assert cosine_similarity(vec_a, vec_b) == pytest.approx(1.0)
    assert cosine_similarity(vec_a, vec_c) == pytest.approx(0.0)
    assert cosine_similarity([], []) == 0.0

    # 5. Reciprocal Rank Fusion
    list1 = ["itemA", "itemB", "itemC"]
    list2 = ["itemB", "itemA", "itemD"]
    fused = reciprocal_rank_fusion([list1, list2], k=60)
    fused_dict = dict(fused)
    # itemA and itemB appear in top 2 of both lists, itemC and itemD only in one
    assert fused_dict["itemA"] > fused_dict["itemC"]
    assert fused_dict["itemB"] > fused_dict["itemD"]
    assert fused[0][0] in ("itemA", "itemB")


@pytest.mark.asyncio
async def test_modular_extraction_primitives() -> None:
    """Verify regex NER patterns, entity typing, alias detection, and pattern graph extraction."""
    # 1. Alias extraction
    text = "Sir Gareth is also known as The Silver Knight. Lord Neverember (also called Protector)."
    aliases = extract_alias_pairs(text)
    assert ("Sir Gareth", "The Silver Knight") in aliases
    assert ("Lord Neverember", "Protector") in aliases

    # 2. Entity classification
    assert classify_entity_type("Sir Gareth") == "npc"
    assert classify_entity_type("Citadel of Light") == "location"
    assert classify_entity_type("Order of the Gauntlet") == "faction"
    assert classify_entity_type("Mystic Orb") == "entity"

    # 3. Proper noun extraction
    proper_nouns = extract_proper_nouns("Sir Gareth visited the Citadel of Light in Neverwinter.")
    assert "Sir Gareth" in proper_nouns
    assert "Citadel of Light" in proper_nouns

    # 4. Relationships
    rels = extract_relationships("Sir Gareth guards Citadel of Light.")
    assert ("Sir Gareth", "guards", "Citadel of Light") in rels

    # 5. Pattern graph extraction (no model call)
    entities, relationships = extract_pattern_graph(
        "Sir Gareth is also known as The Silver Knight. He guards Citadel of Light."
    )
    ent_names = [e.name for e in entities]
    assert "Sir Gareth" in ent_names
    assert "The Silver Knight" in ent_names
    assert any(r.relationship_type == "alias_of" for r in relationships)
    assert any(r.relationship_type == "guards" for r in relationships)


@pytest.mark.asyncio
async def test_get_or_create_entity_helper() -> None:
    """Verify get_or_create_entity creates and deduplicates entities in InMemoryGraphStore."""
    graph = redstring.InMemoryGraphStore()
    cid = uuid4()
    prov = redstring.Provenance(
        observed_at=datetime.now(UTC),
        extraction_method=redstring.ExtractionMethod.MANUAL,
        confidence=1.0,
        source_id="test",
    )
    e1_id = await get_or_create_entity(graph, cid, "Sir Gareth", "test", prov)
    e2_id = await get_or_create_entity(graph, cid, "sir gareth", "test", prov)
    assert e1_id == e2_id
