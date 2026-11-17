"""Embedding provider factory for Runefoble services.

The port is `redstring.EmbeddingProvider`. This package maps configuration to an adapter.
"""

from runefoble_embeddings.providers import build_openai_compatible_provider

__all__ = ["build_openai_compatible_provider"]
