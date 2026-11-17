"""Composition root for the Campaign Lore retrieval engine.

Builds each port from its settings. The engine receives its ports through its
constructor and never chooses an adapter. Start-up fails when a configured backend
is unreachable. No port falls back to an in-process or fake adapter (ADR-0015).
"""

from typing import assert_never

import redstring
from redstring.vector.adapters.pgvector import PgVectorStore
from runefoble_embeddings import build_openai_compatible_provider
from runefoble_platform.config import EmbeddingEndpointSettings, LoreBackendSettings

from campaign_lore.retrieval import LoreRetrievalEngine

LORE_VECTOR_TABLE = "lore_entity_vectors"
START_UP_PROBE_TEXT = "campaign lore start-up probe"


async def _build_embeddings(endpoint: EmbeddingEndpointSettings) -> redstring.EmbeddingProvider:
    """Build the provider and prove the endpoint answers with the configured width.

    Raises:
        ValueError: A required endpoint setting is missing.
        RuntimeError: The endpoint does not answer, or answers with the wrong width.
    """
    provider = build_openai_compatible_provider(endpoint)
    try:
        await provider.embed([START_UP_PROBE_TEXT])
    except redstring.EmbeddingProviderError as error:
        raise RuntimeError(
            "Campaign Lore embedding endpoint is unreachable or returned an invalid "
            f"response at {endpoint.base_url}: {error}"
        ) from error
    return provider


async def _connect_pgvector(database_url: str, dimension: int) -> redstring.VectorStore:
    """Connect the pgvector entity store and create its schema if it is missing."""
    # SQLAlchemy's driver dialect is not a libpq or asyncpg DSN.
    dsn = database_url.replace("postgresql+asyncpg://", "postgresql://", 1)
    try:
        store = await PgVectorStore.connect(dsn, dimension=dimension, table=LORE_VECTOR_TABLE)
    except Exception as error:
        raise RuntimeError(
            f"Campaign Lore vector store (PostgreSQL) is unreachable: {error}"
        ) from error
    try:
        await store.ensure_schema()
    except BaseException:
        await store.close()
        raise
    return store


async def _build_vectors(choice: str, database_url: str, dimension: int) -> redstring.VectorStore:
    match choice:
        case "pgvector":
            return await _connect_pgvector(database_url, dimension)
        case _:
            assert_never(choice)


def _build_graph(choice: str) -> redstring.GraphStore:
    match choice:
        case "projection":
            return redstring.InMemoryGraphStore()
        case _:
            assert_never(choice)


def _build_chunks(choice: str, dimension: int) -> redstring.ChunkStore:
    match choice:
        case "memory":
            return redstring.InMemoryChunkStore(dimension=dimension)
        case _:
            assert_never(choice)


async def build_retrieval_engine(
    settings: LoreBackendSettings,
    endpoint: EmbeddingEndpointSettings,
    database_url: str,
) -> LoreRetrievalEngine:
    """Construct an empty retrieval engine. Call rebuild_lore_projection to fill it.

    Raises:
        ValueError: A required embedding setting is missing.
        RuntimeError: The embedding endpoint or the PostgreSQL vector store is unreachable.
    """
    embeddings = await _build_embeddings(endpoint)
    dimension = embeddings.dimension
    return LoreRetrievalEngine(
        embeddings=embeddings,
        graph=_build_graph(settings.graph),
        vectors=await _build_vectors(settings.vector, database_url, dimension),
        chunks=_build_chunks(settings.chunk, dimension),
    )
