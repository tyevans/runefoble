"""Composition root for the Rules Compendium retrieval engine.

Chooses the retrieval mode from RulesCompendiumSettings. The engine receives its
provider through its constructor and never reads settings.
"""

from typing import assert_never

from runefoble_embeddings import build_openai_compatible_provider
from runefoble_platform.config import EmbeddingEndpointSettings, RulesCompendiumSettings

from rules_compendium.retrieval import CompendiumRetrievalEngine


def build_retrieval_engine(
    settings: RulesCompendiumSettings,
    endpoint: EmbeddingEndpointSettings,
) -> CompendiumRetrievalEngine:
    """Construct an empty retrieval engine. Call initialize_srd_data before serving searches.

    Raises:
        ValueError: The configured provider is missing a required endpoint setting.
    """
    match settings.embedding:
        case "lexical":
            return CompendiumRetrievalEngine(embeddings=None)
        case "openai_compatible":
            return CompendiumRetrievalEngine(
                embeddings=build_openai_compatible_provider(endpoint),
            )
        case _:
            assert_never(settings.embedding)
