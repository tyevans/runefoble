# How-To: Index Campaign Lore & Execute redstring Hybrid RAG

This guide explains how to ingest campaign worldbuilding documents, extract knowledge graphs and relationships with `redstring`, consolidate entity aliases, and perform sub-50ms hybrid RAG search protected by SpiceDB Zanzibar authorization.

---

## 1. Document Ingestion

To ingest a new markdown or text worldbuilding document into the campaign knowledge base:

```bash
curl -X POST http://localhost:8006/api/v1/lore/documents \
  -H "Content-Type: application/json" \
  -H "x-user-id: user-dm-1" \
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
1. Creates an event-sourced `LoreDocumentAggregate` and emits `LoreDocumentIngested`.
2. Passes the document through `redstring.build_graph` to build semantic embeddings, lexical BM25 chunks, and knowledge graph projections.
3. Records extracted entities on the aggregate stream via `EntitiesExtracted`.
4. Writes SpiceDB Zanzibar relationship tuples binding the document to the campaign.

---

## 2. Consolidating Entity Aliases

When NPCs or factions hold multiple titles, aliases, or secret identities, consolidate them into a single canonical node using `redstring.Consolidator`:

```bash
curl -X POST http://localhost:8006/api/v1/lore/aliases/consolidate \
  -H "Content-Type: application/json" \
  -d '{
    "campaign_id": "8a329ef2-5c91-4cf1-83d8-21d4bb67f101",
    "canonical_name": "Sir Gareth",
    "alias_name": "The Silver Knight",
    "reason": "Honorary knighthood title"
  }'
```

To resolve aliases during dialogue generation or intent extraction:

```bash
curl -X GET "http://localhost:8006/api/v1/lore/aliases/resolve?campaign_id=8a329ef2-5c91-4cf1-83d8-21d4bb67f101&name=The+Silver+Knight"
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
  -H "x-user-id: user-player-2" \
  -d '{
    "campaign_id": "8a329ef2-5c91-4cf1-83d8-21d4bb67f101",
    "query": "Where is the Citadel of Light located?",
    "limit": 5,
    "include_graph_walk": true
  }'
```

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

## 5. Modular Retrieval Architecture

To comply with Hard Invariant 6 (File length limit < 500 lines) and enable independent optimization of worldbuilding heuristics and search algorithms, campaign lore retrieval is partitioned into dedicated submodules:

- **Entity & Alias Extraction (`extraction.py`)**: Implements `WorldbuildingLlmProvider`, heuristic NER pattern scanning, entity classification (`npc`, `location`, `faction`), and alias detection.
- **Scoring Primitives (`scoring.py`)**: Implements Okapi BM25 tokenization (`tokenize`), BM25 term weighting (`bm25_term_score`), inverse document frequency (`compute_idf`), dense vector similarity (`cosine_similarity`), and Reciprocal Rank Fusion (`reciprocal_rank_fusion`).
- **Data Models (`models.py`)**: Defines `DocumentMetadata` and `LoreSearchResultItem` data classes.
- **Engine Coordinator (`retrieval.py`)**: Exposes `LoreRetrievalEngine` (aliased as `HybridLoreEngine`), managing document ingestion, knowledge graph neighbor traversal, alias consolidation, and hybrid search query execution.

All submodules re-export their public symbols through `campaign_lore` and `campaign_lore.retrieval` to guarantee full backward compatibility.

