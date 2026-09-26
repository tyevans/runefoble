"""Lexical and vector retrieval scoring primitives for campaign lore.

Includes BM25 tokenization, term scoring, cosine similarity, and Reciprocal Rank Fusion.
"""

import math
import re
from collections.abc import Hashable, Sequence


def tokenize(text: str) -> list[str]:
    """Tokenize text into lowercase alphanumeric terms for lexical search."""
    return [term.lower() for term in re.findall(r"\b\w+\b", text) if term]


def compute_idf(doc_freq: int, total_docs: int) -> float:
    """Calculate Robertson-Spärck Jones BM25 inverse document frequency.

    Formula: ln(1 + (N - n + 0.5) / (n + 0.5))
    """
    if total_docs <= 0 or doc_freq < 0:
        return 0.0
    return math.log(1.0 + (total_docs - doc_freq + 0.5) / (doc_freq + 0.5))


def bm25_term_score(
    tf: int,
    doc_len: int,
    avg_doc_len: float,
    k1: float = 1.5,
    b: float = 0.75,
) -> float:
    """Calculate Okapi BM25 term frequency saturation component."""
    if tf <= 0 or avg_doc_len <= 0:
        return 0.0
    len_norm = 1.0 - b + b * (doc_len / avg_doc_len)
    return (tf * (k1 + 1.0)) / (tf + k1 * len_norm)


def bm25_score(
    query_tokens: list[str],
    doc_tokens: list[str],
    idf_map: dict[str, float],
    avg_doc_len: float,
    k1: float = 1.5,
    b: float = 0.75,
) -> float:
    """Calculate full BM25 lexical relevance score for a document."""
    if not query_tokens or not doc_tokens or avg_doc_len <= 0:
        return 0.0
    doc_len = len(doc_tokens)
    tf_counts: dict[str, int] = {}
    for token in doc_tokens:
        tf_counts[token] = tf_counts.get(token, 0) + 1

    score = 0.0
    for q_term in set(query_tokens):
        tf = tf_counts.get(q_term, 0)
        if tf > 0:
            idf = idf_map.get(q_term, 0.0)
            term_score = bm25_term_score(tf, doc_len, avg_doc_len, k1=k1, b=b)
            score += idf * term_score
    return score


def cosine_similarity(
    vec_a: Sequence[float],
    vec_b: Sequence[float],
) -> float:
    """Calculate cosine similarity between two dense embedding vectors."""
    if len(vec_a) != len(vec_b) or not vec_a:
        return 0.0
    dot_prod = sum(a * b for a, b in zip(vec_a, vec_b, strict=False))
    norm_a = math.sqrt(sum(a * a for a in vec_a))
    norm_b = math.sqrt(sum(b * b for b in vec_b))
    if norm_a == 0.0 or norm_b == 0.0:
        return 0.0
    return float(dot_prod / (norm_a * norm_b))


def reciprocal_rank_fusion[T: Hashable](
    ranked_lists: Sequence[Sequence[T]],
    k: int = 60,
) -> list[tuple[T, float]]:
    """Fuse multiple ranked result lists using Reciprocal Rank Fusion (RRF).

    Formula: RRF_score(d) = sum(1 / (k + rank_i(d)))
    """
    scores: dict[T, float] = {}
    for ranked in ranked_lists:
        for rank, item in enumerate(ranked, start=1):
            scores[item] = scores.get(item, 0.0) + (1.0 / (k + rank))
    return sorted(scores.items(), key=lambda x: x[1], reverse=True)


__all__ = [
    "bm25_score",
    "bm25_term_score",
    "compute_idf",
    "cosine_similarity",
    "reciprocal_rank_fusion",
    "tokenize",
]
