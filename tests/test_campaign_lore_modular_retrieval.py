"""Tests verifying modular decomposition and backward compatibility of campaign_lore retrieval submodules."""

from __future__ import annotations

from datetime import UTC, datetime
from pathlib import Path
from uuid import uuid4

import pytest
import redstring
from campaign_lore import (
    DocumentMetadata,
    HybridLoreEngine,
    LoreRetrievalEngine,
    LoreSearchResultItem,
    WorldbuildingLlmProvider,
    bm25_score,
    bm25_term_score,
    classify_entity_type,
    compute_idf,
    cosine_similarity,
    extract_alias_pairs,
    extract_proper_nouns,
    extract_relationships,
    reciprocal_rank_fusion,
    tokenize,
)
from campaign_lore.extraction import (
    WorldbuildingLlmProvider as ExtractionProvider,
)
from campaign_lore.extraction import (
    get_or_create_entity,
)
from campaign_lore.retrieval import (
    DocumentMetadata as RetrievalMeta,
)
from campaign_lore.retrieval import (
    HybridLoreEngine as RetrievalHybridEngine,
)
from campaign_lore.retrieval import (
    LoreRetrievalEngine as RetrievalEngine,
)
from campaign_lore.retrieval import (
    LoreSearchResultItem as RetrievalItem,
)
from campaign_lore.retrieval import (
    WorldbuildingLlmProvider as RetrievalProvider,
)
from campaign_lore.scoring import (
    bm25_score as scoring_bm25_score,
)
from campaign_lore.scoring import (
    cosine_similarity as scoring_cosine_similarity,
)
from campaign_lore.scoring import (
    reciprocal_rank_fusion as scoring_rrf,
)
from campaign_lore.scoring import (
    tokenize as scoring_tokenize,
)
from pydantic import BaseModel


def test_import_from_subpackage_facade() -> None:
    """Verify that importing from campaign_lore exposes all public symbols."""
    assert LoreRetrievalEngine is not None
    assert HybridLoreEngine is LoreRetrievalEngine
    assert DocumentMetadata is not None
    assert LoreSearchResultItem is not None
    assert WorldbuildingLlmProvider is not None
    assert callable(tokenize)
    assert callable(compute_idf)
    assert callable(bm25_term_score)
    assert callable(bm25_score)
    assert callable(cosine_similarity)
    assert callable(reciprocal_rank_fusion)
    assert callable(classify_entity_type)
    assert callable(extract_alias_pairs)
    assert callable(extract_proper_nouns)
    assert callable(extract_relationships)


def test_import_from_retrieval_backward_compatibility() -> None:
    """Verify campaign_lore.retrieval preserves 100% backward compatibility."""
    assert RetrievalEngine is LoreRetrievalEngine
    assert RetrievalHybridEngine is LoreRetrievalEngine
    assert RetrievalMeta is DocumentMetadata
    assert RetrievalItem is LoreSearchResultItem
    assert RetrievalProvider is WorldbuildingLlmProvider
    assert ExtractionProvider is WorldbuildingLlmProvider


def test_modular_scoring_primitives() -> None:
    """Verify BM25 tokenization, term scoring, cosine similarity, and RRF rank fusion."""
    # 1. Tokenization
    tokens = scoring_tokenize("Sir Gareth, the Silver Knight of Neverwinter!")
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
    score1 = scoring_bm25_score(["sunblade"], doc1, idf_map, avg_doc_len=5.0)
    score2 = scoring_bm25_score(["sunblade"], doc2, idf_map, avg_doc_len=5.0)
    assert score1 > 0.0
    assert score2 == 0.0

    # 4. Cosine similarity
    vec_a = [1.0, 0.0, 0.0]
    vec_b = [1.0, 0.0, 0.0]
    vec_c = [0.0, 1.0, 0.0]
    assert scoring_cosine_similarity(vec_a, vec_b) == pytest.approx(1.0)
    assert scoring_cosine_similarity(vec_a, vec_c) == pytest.approx(0.0)
    assert scoring_cosine_similarity([], []) == 0.0

    # 5. Reciprocal Rank Fusion
    list1 = ["itemA", "itemB", "itemC"]
    list2 = ["itemB", "itemA", "itemD"]
    fused = scoring_rrf([list1, list2], k=60)
    fused_dict = dict(fused)
    # itemA and itemB appear in top 2 of both lists, itemC and itemD only in one
    assert fused_dict["itemA"] > fused_dict["itemC"]
    assert fused_dict["itemB"] > fused_dict["itemD"]
    assert fused[0][0] in ("itemA", "itemB")


@pytest.mark.asyncio
async def test_modular_extraction_primitives() -> None:
    """Verify heuristic NER regexes, entity typing, alias detection, and LLM extraction."""
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

    # 5. WorldbuildingLlmProvider extraction
    provider = WorldbuildingLlmProvider()

    class ExtractionSchema(BaseModel):
        entities: list[redstring.ExtractedEntity]
        relationships: list[redstring.ExtractedRelationship]

    extracted = await provider.extract(
        "Sir Gareth is also known as The Silver Knight. He guards Citadel of Light.",
        schema=ExtractionSchema,
    )
    ent_names = [e.name for e in extracted.entities]
    assert "Sir Gareth" in ent_names
    assert "The Silver Knight" in ent_names
    assert any(r.relationship_type == "alias_of" for r in extracted.relationships)
    assert any(r.relationship_type == "guards" for r in extracted.relationships)


@pytest.mark.asyncio
async def test_get_or_create_entity_helper() -> None:
    """Verify get_or_create_entity creates and deduplicates entities in InMemoryGraphStore."""
    graph = redstring.InMemoryGraphStore()
    cid = uuid4()
    prov = redstring.Provenance(
        observed_at=datetime.now(UTC),
        extraction_method=redstring.ExtractionMethod.LLM,
        confidence=1.0,
        source_id="test",
    )
    e1_id = await get_or_create_entity(graph, cid, "Sir Gareth", prov)
    e2_id = await get_or_create_entity(graph, cid, "sir gareth", prov)
    assert e1_id == e2_id


def test_file_length_invariants() -> None:
    """Verify Hard Invariant 6 and TASK-0089 file length limits (< 220 lines)."""
    base_dir = Path("services/campaign_lore/src/campaign_lore")
    target_files = ["retrieval.py", "extraction.py", "scoring.py", "models.py"]

    for fname in target_files:
        path = base_dir / fname
        assert path.exists(), f"File {fname} missing"
        line_count = len(path.read_text().splitlines())
        assert line_count < 220, f"{fname} has {line_count} lines, exceeding 220 limit"
