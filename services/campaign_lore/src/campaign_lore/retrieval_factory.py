"""Composition root for the Campaign Lore retrieval engine.

Builds each port from LoreBackendSettings. The engine itself receives its ports
through its constructor and never chooses an adapter.
"""

from typing import assert_never

import redstring
from runefoble_platform.config import LoreBackendSettings

from campaign_lore.retrieval import LoreRetrievalEngine


def _build_embeddings(choice: str) -> redstring.EmbeddingProvider:
    match choice:
        case "fake":
            return redstring.FakeEmbeddingProvider()
        case _:
            assert_never(choice)


def _build_graph(choice: str) -> redstring.GraphStore:
    match choice:
        case "projection":
            return redstring.InMemoryGraphStore()
        case _:
            assert_never(choice)


def _build_vectors(choice: str, dimension: int) -> redstring.VectorStore:
    match choice:
        case "memory":
            return redstring.InMemoryVectorStore(dimension=dimension)
        case _:
            assert_never(choice)


def _build_chunks(choice: str, dimension: int) -> redstring.ChunkStore:
    match choice:
        case "memory":
            return redstring.InMemoryChunkStore(dimension=dimension)
        case _:
            assert_never(choice)


def build_retrieval_engine(settings: LoreBackendSettings) -> LoreRetrievalEngine:
    """Construct an empty retrieval engine. Call rebuild_lore_projection to fill it."""
    embeddings = _build_embeddings(settings.embedding)
    dimension = embeddings.dimension
    return LoreRetrievalEngine(
        embeddings=embeddings,
        graph=_build_graph(settings.graph),
        vectors=_build_vectors(settings.vector, dimension),
        chunks=_build_chunks(settings.chunk, dimension),
    )
