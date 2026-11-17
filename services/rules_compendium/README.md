# Rules Compendium & Automated Encounter Builder Microservice

TTRPG rules compendium and automated Challenge Rating (CR) encounter builder for Runefoble.

Powered by `redstring` for rule retrieval and `eventsource-py` for event sourcing. Exposes public REST endpoints and FastMCP tools for rule lookups and mathematical encounter balancing.

## Retrieval Mode

- `lexical` (default): BM25 keyword ranking only. Responses report `"retrieval_mode": "lexical"`.
- `hybrid`: BM25 fused with vector search from an OpenAI-compatible embeddings endpoint. Set `RUNEFOBLE_RULES_EMBEDDING=openai_compatible` and the `RUNEFOBLE_EMBEDDING_*` settings. Responses report `"retrieval_mode": "hybrid"`.

The sub-50ms budget applies to `lexical` mode. Hybrid search adds one embedding call per query.

See [Embedding Providers](../../docs/reference/embedding-providers.md) and [Platform Services](../../docs/reference/platform-services.md#rules-compendium-retrieval-mode).
