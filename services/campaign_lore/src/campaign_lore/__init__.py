"""Campaign Lore Knowledge Base & redstring RAG Microservice."""

from campaign_lore.extraction import (
    classify_entity_type,
    extract_alias_pairs,
    extract_pattern_graph,
    extract_proper_nouns,
    extract_relationships,
)
from campaign_lore.retrieval import (
    DocumentMetadata,
    LoreRetrievalEngine,
    LoreSearchResultItem,
)
from campaign_lore.scoring import (
    bm25_score,
    bm25_term_score,
    compute_idf,
    cosine_similarity,
    reciprocal_rank_fusion,
    tokenize,
)

__all__ = [
    "DocumentMetadata",
    "LoreRetrievalEngine",
    "LoreSearchResultItem",
    "bm25_score",
    "bm25_term_score",
    "classify_entity_type",
    "compute_idf",
    "cosine_similarity",
    "extract_alias_pairs",
    "extract_pattern_graph",
    "extract_proper_nouns",
    "extract_relationships",
    "reciprocal_rank_fusion",
    "tokenize",
]
