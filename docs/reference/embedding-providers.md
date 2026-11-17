# Reference: Embedding Providers

Services that search by meaning use an embedding provider. This page lists the port, the
factory that builds it, the settings that select it, and the failure rules.

## Port

The port is `redstring.EmbeddingProvider`. A provider exposes:

| Member | Meaning |
|---|---|
| `dimension` | Vector width. Fixed for the life of the provider. |
| `embed(texts)` | One vector per indexed text, in order. Used at index time. |
| `embed_query(texts)` | One vector per search query, in order. Used at search time. |

Services depend on this port only. They do not import an adapter class.

## Package

`libs/runefoble_embeddings` (`runefoble-embeddings`) maps settings to adapters.

| Function | Input | Output |
|---|---|---|
| `build_openai_compatible_provider(endpoint)` | `EmbeddingEndpointSettings` | `redstring.EmbeddingProvider` |

The function covers any OpenAI-compatible `/v1/embeddings` server. This includes Ollama,
llama.cpp, vLLM, LM Studio, and OpenAI.

## Settings

Settings come from the process environment. They are read when the service starts.

### Endpoint (`EmbeddingEndpointSettings`, prefix `RUNEFOBLE_EMBEDDING_`)

| Variable | Default | Required by `openai_compatible` | Meaning |
|---|---|---|---|
| `RUNEFOBLE_EMBEDDING_BASE_URL` | none | yes | Base URL, including `/v1`. Example: `http://ollama:11434/v1`. |
| `RUNEFOBLE_EMBEDDING_MODEL` | none | yes | Model name sent to the endpoint. Also recorded as provenance. |
| `RUNEFOBLE_EMBEDDING_DIMENSION` | none | yes | Vector width the model returns. Must be positive. |
| `RUNEFOBLE_EMBEDDING_API_KEY` | `not-needed` | no | Bearer key. Local servers ignore it. |
| `RUNEFOBLE_EMBEDDING_DOCUMENT_PREFIX` | empty | no | Text added before each indexed document. Needed by some asymmetric models. |
| `RUNEFOBLE_EMBEDDING_QUERY_PREFIX` | empty | no | Text added before each search query. Needed by some asymmetric models. |

### Campaign Lore selection (`LoreBackendSettings`, prefix `RUNEFOBLE_LORE_`)

| Variable | Default | Values | Effect |
|---|---|---|---|
| `RUNEFOBLE_LORE_EMBEDDING` | `openai_compatible` | `openai_compatible` | The only choice. The endpoint settings above are required. |
| `RUNEFOBLE_LORE_VECTOR` | `pgvector` | `pgvector` | The only choice. Entity vectors go to the `lore_entity_vectors` table. |

`campaign_lore` checks the endpoint at start-up. It sends one probe text and requires a vector of the configured width. A failed probe stops start-up with `embedding endpoint is unreachable`. Campaign Lore has no fake embedder and no in-memory vector store in production settings.

### Rules Compendium selection (`RulesCompendiumSettings`, prefix `RUNEFOBLE_RULES_`)

| Variable | Default | Values | Effect |
|---|---|---|---|
| `RUNEFOBLE_RULES_EMBEDDING` | `lexical` | `lexical`, `openai_compatible` | `lexical` ranks with BM25 only. `openai_compatible` adds vector search. |

## Failure rules

- **Missing setting.** If `openai_compatible` lacks a required variable, the service
  does not start. The error names each missing variable.
- **Invalid dimension.** A dimension that is not positive stops start-up.
- **Dimension mismatch at run time.** The adapter raises `EmbeddingProviderError` when a
  vector has a different width from `RUNEFOBLE_EMBEDDING_DIMENSION`.
- **Endpoint down at start-up.** Campaign Lore stops, because its start-up probe fails.
  Rules Compendium does not probe at start-up. Its searches fail while the endpoint is down.
- **Endpoint down at run time.** Search that needs a query vector fails. The service does
  not switch to lexical results silently.
- **No hash fallback.** No service uses hash vectors in production. Hash embeddings exist
  only as test doubles.

## Latency

Each search in `hybrid` mode calls `embed_query` once. Round trips to a remote endpoint
add to the search time. The sub-50 ms budget in the Rules Compendium applies to `lexical`
mode. Measure `hybrid` mode against the real endpoint.

## Adding a provider

1. Add a literal to the selection setting in `libs/runefoble_platform` config.
2. Add a builder function in `libs/runefoble_embeddings`. Check every required field
   before the adapter is built.
3. Add a `case` to the service's retrieval factory. The `assert_never` branch fails the
   type check if a case is missing.
4. Add blackbox tests. Start a stand-in endpoint with `tests/helpers/live_services.py` and
   set the variables through the environment.

## Related

- [Rules Compendium how-to](../how-to/balance-combat-encounters-and-query-compendium.md)
- [Platform services reference](platform-services.md)
