"""Build `redstring` embedding providers from `EmbeddingEndpointSettings`.

A missing endpoint setting raises at construction. The service then fails to
start, which is the intent. A provider never falls back to hash vectors.
"""

import redstring
from redstring.llm.adapters.langchain_embedding import LangChainEmbeddingProvider
from runefoble_platform.config import EmbeddingEndpointSettings


def build_openai_compatible_provider(
    endpoint: EmbeddingEndpointSettings,
) -> redstring.EmbeddingProvider:
    """Build an embedding provider for an OpenAI-compatible `/v1/embeddings` endpoint.

    Raises:
        ValueError: A required endpoint setting is missing, or the dimension is not positive.
    """
    base_url = endpoint.base_url
    model = endpoint.model
    dimension = endpoint.dimension
    if base_url is None or model is None or dimension is None:
        missing = [
            name
            for name, value in (
                ("RUNEFOBLE_EMBEDDING_BASE_URL", base_url),
                ("RUNEFOBLE_EMBEDDING_MODEL", model),
                ("RUNEFOBLE_EMBEDDING_DIMENSION", dimension),
            )
            if value is None
        ]
        raise ValueError(
            "openai_compatible embedding provider needs these settings: " + ", ".join(missing)
        )
    if dimension <= 0:
        raise ValueError("RUNEFOBLE_EMBEDDING_DIMENSION must be a positive integer")

    return LangChainEmbeddingProvider.openai_compatible(
        base_url=base_url,
        model=model,
        dimension=dimension,
        api_key=endpoint.api_key,
        document_prefix=endpoint.document_prefix,
        query_prefix=endpoint.query_prefix,
    )
