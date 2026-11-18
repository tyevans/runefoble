# How-To: Index Campaign Lore & Execute redstring Hybrid RAG

This guide explains how to ingest campaign worldbuilding documents, extract knowledge graphs and relationships with `redstring`, consolidate entity aliases, and perform sub-50ms hybrid RAG search protected by SpiceDB Zanzibar authorization.

## Caller Identity

Every Campaign Lore route needs a verified bearer token. The service checks the RS256 signature, issuer, audience, and expiry. Without a valid token it returns `401`. The caller is the token subject (`sub`). Campaign Lore never reads the caller from a body field, a query parameter, or an identity header. The public routes are `/health`, `/healthz`, `/openapi.json`, and `/ui/manifest`.

Set `$DM_TOKEN` and `$PLAYER_TOKEN` to tokens that Zitadel issued for each user. The examples below use them.

Each route checks one SpiceDB Zanzibar permission on the campaign:

- Document ingest and alias consolidation need `run_session` (DM, GM, or owner). Other callers receive `403`.
- Search and secret chunks follow the rules in [Authorization Filtering](#authorization-filtering-spicedb-zanzibar).

---

## 1. Document Ingestion

To ingest a new markdown or text worldbuilding document into the campaign knowledge base:

```bash
curl -X POST http://localhost:8006/api/v1/lore/documents \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer $DM_TOKEN" \
  -d '{
    "campaign_id": "8a329ef2-5c91-4cf1-83d8-21d4bb67f101",
    "title": "The Knights of the Silver Dawn",
    "content": "Sir Gareth is also known as The Silver Knight. He guards the Citadel of Light in Neverwinter.",
    "is_secret": false,
    "tags": ["factions", "paladins"]
  }'
```

### Response
```json
{
  "document_id": "3c89b218-0f04-45aa-b883-9bca4020a101",
  "campaign_id": "8a329ef2-5c91-4cf1-83d8-21d4bb67f101",
  "title": "The Knights of the Silver Dawn",
  "is_secret": false,
  "entities_count": 3,
  "relationships_count": 2,
  "chunks_count": 1,
  "status": "indexed"
}
```

This endpoint:
1. Creates an event-sourced `LoreDocumentAggregate` and emits `runefoble.events.lore.document_ingested`. The repository publishes it to the stream `runefoble.events.lore.document_ingested` before the save returns.
2. Extracts entities, aliases, and relationships with regex patterns. No model is called. Each entity records `extraction_method: "pattern"`.
3. Indexes the graph, the BM25 and dense chunk corpus, and the entity vectors in the service process.
4. Records extracted entities on the aggregate stream via `runefoble.events.lore.entities_extracted`.
5. Writes SpiceDB Zanzibar relationship tuples binding the document to the campaign.

---

## 2. Consolidating Entity Aliases

When NPCs or factions hold multiple titles, aliases, or secret identities, consolidate them into a single canonical node using `redstring.Consolidator`:

```bash
curl -X POST http://localhost:8006/api/v1/lore/aliases/consolidate \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer $DM_TOKEN" \
  -d '{
    "campaign_id": "8a329ef2-5c91-4cf1-83d8-21d4bb67f101",
    "canonical_name": "Sir Gareth",
    "alias_name": "The Silver Knight",
    "reason": "Honorary knighthood title",
    "document_id": "3c89b218-0f04-45aa-b883-9bca4020a101"
  }'
```

`document_id` is required. The service records the consolidation on that document's stream as `runefoble.events.lore.aliases_consolidated`, so it survives a restart. An unknown document returns `404`.

Status codes for this route:

- `200`: The merge is recorded.
- `404`: The document does not exist, or it belongs to another campaign.
- `409`: The alias or the canonical entity is already merged. Nothing is written. A repeated call with the same names returns `409`. Read the `detail` field for the reason.
- `503`: The service has not finished start-up. Retry later. The service does not return a substitute result.

To resolve aliases during dialogue generation or intent extraction:

```bash
curl -X GET "http://localhost:8006/api/v1/lore/aliases/resolve?campaign_id=8a329ef2-5c91-4cf1-83d8-21d4bb67f101&name=The+Silver+Knight" \
  -H "Authorization: Bearer $PLAYER_TOKEN"
```

Output:
```json
{
  "campaign_id": "8a329ef2-5c91-4cf1-83d8-21d4bb67f101",
  "input_name": "The Silver Knight",
  "canonical_name": "Sir Gareth",
  "is_alias": true
}
```

---

## 3. Sub-50ms Hybrid RAG Retrieval

Execute hybrid search queries fusing dense vector similarity, BM25 lexical keyword matching, and 1-hop graph neighbor walks:

```bash
curl -X POST http://localhost:8006/api/v1/lore/search \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer $PLAYER_TOKEN" \
  -d '{
    "campaign_id": "8a329ef2-5c91-4cf1-83d8-21d4bb67f101",
    "query": "Where is the Citadel of Light located?",
    "limit": 5,
    "include_graph_walk": true
  }'
```

The request body has only `campaign_id`, `query`, `limit`, and `include_graph_walk`. A body with any other field, such as `caller_id`, returns `422`. The caller is the verified token subject, so a client cannot choose another caller.

### Authorization Filtering (SpiceDB Zanzibar)

- If the caller possesses `run_session` permission (DM, GM, or Campaign Owner), `can_read_secrets` evaluates to `true`, and both public and secret DM notes are returned.
- If the caller is a standard player or spectator, `can_read_secrets` evaluates to `false`, and all chunks originating from secret documents are omitted from the results.

---

## 4. Microfrontend Codex Component

The Campaign Lore bounded context vendors the Lit Web Component `<runefoble-campaign-codex>` exposed at `/ui/manifest`.

To embed the player codex in Lit:

```ts
import '@runefoble/campaign-lore-ui';

html`
  <runefoble-campaign-codex
    campaignId="8a329ef2-5c91-4cf1-83d8-21d4bb67f101"
    .isDM=${false}
    .entries=${loreEntries}
  ></runefoble-campaign-codex>
`;
```

---

## 5. Backends, Start-up Replay, and Restarts

The retrieval engine is built from `LoreBackendSettings` (`RUNEFOBLE_LORE_*`, see the platform services reference). The entity vector index is a pgvector table on the platform PostgreSQL database. The graph and the passage corpus are in process and derived. At start-up the service replays every `LoreDocument` event from the event store into a fresh engine. Then it accepts requests.

### Required settings

The service has no fake or in-memory vector backend. It needs these settings:

- **`RUNEFOBLE_EMBEDDING_BASE_URL`**, **`RUNEFOBLE_EMBEDDING_MODEL`**, **`RUNEFOBLE_EMBEDDING_DIMENSION`**: The OpenAI-compatible `/v1/embeddings` endpoint. Start-up names each missing setting and stops.
- **`RUNEFOBLE_EMBEDDING_API_KEY`**: Optional for local servers. In Kubernetes, the Helm chart reads it from the Secret `campaign-lore-embedding`, key `api-key`. You create that Secret. The chart does not.
- **`RUNEFOBLE_DATABASE_URL`**: The PostgreSQL database that holds the pgvector table `lore_entity_vectors`. The service creates the `vector` extension and the table at start-up. The PostgreSQL server must provide the `pgvector` extension. The chart uses the `pgvector/pgvector:pg16` image.

### Start-up failures

The service stops with an error when one of these checks fails. It does not serve a partial or fallback search.

- The embedding endpoint does not answer the start-up probe, or it returns a different width. The error contains `embedding endpoint is unreachable`.
- PostgreSQL does not accept the pgvector connection. The error contains `vector store (PostgreSQL) is unreachable`.
- `RUNEFOBLE_EVENT_STORE_BACKEND=postgresql` (the default) and PostgreSQL cannot be reached. The service does not serve an empty projection.
- Redis Streams is unreachable, or `RUNEFOBLE_REDIS_URL` is empty. The service cannot publish lore events, so it does not start.

### Restarts

- Document titles, secrecy, aliases, and search results survive a restart, because they come from the replayed events.
- Codex entries survive a restart. `GET /api/v1/campaigns/{campaign_id}/codex/entries` reads the `runefoble.events.lore.codex_entry_published` events from the event store on each request. No process keeps a codex index.
- Every committed lore event is published to its `runefoble.events.lore.<name>` stream. The table is in [Campaign Lore Stream Topics](../reference/events-catalog-world-media.md#campaign-lore-stream-topics). A publish failure returns `503`, and the client retries.
- Entity identifiers are derived from the campaign, document, name, and type. A restart writes the same pgvector rows again. It adds no duplicate rows.
- Replay time grows with the number of stored documents. Each start re-indexes them.
- The passage corpus stays in process. Each start rebuilds it from the events.
