---
id: '0572'
title: Campaign Lore Codex Index, Retrieval State and Domain Events Made Durable
status: Refined
created: 2026-11-17
dependencies:
- TASK-0560
- TASK-0561
governing_adrs:
- ADR-0011
- ADR-0006
- ADR-0007
governing_prds:
- PRD-0007
- PRD-0023
governing_stories:
- US-0036
- US-0050
target_release: 0.9.0
severity: high
source_audits:
- w2-campaign-lore.md
---

# TASK-0572: Campaign Lore Codex Index, Retrieval State and Domain Events Made Durable

## Status
Refined

## Summary
Campaign lore aggregates are stored, but three things that users see are not: the codex list is a module-level dict, the retrieval state (documents, redstring graph, vectors) is in memory, and aggregate events are never published to the bus. This task rebuilds the codex index and retrieval state from the event stream at start-up, and publishes lore events through the repository on the documented topics.

## Problem Statement
- `services/campaign_lore/src/campaign_lore/dependencies.py:37-42` creates repositories without `event_bus`. `dependencies.py:43-61` leaves `event_publisher` as `None` (w2-campaign-lore F11). The events-schema doc lists topics such as `runefoble.events.lore.document_ingested` that are never published.
- `dependencies.py:45`: `_campaign_codex_entries` is a module-level dict. The codex list reads only this dict, so entries disappear after restart (w2-campaign-lore F7).
- `retrieval.py:43`: `_documents` and the redstring graph, vector, and chunk stores are in memory. Search returns nothing after restart (w2-campaign-lore F7, F6).
- `ingest` writes every campaign entity into each document's `EntitiesExtracted` event (w2-campaign-lore F10). This task fixes the payload scope only.
- Alias consolidation and retrieval state bypass aggregates (w2-campaign-lore F9).

## Documentation & Architecture Review
- `docs/how-to/index-campaign-lore-with-redstring.md` describes ingestion and retrieval. Verify it and correct it.
- `docs/reference/events-schema.md` lines 916-978 list the lore topics. Align them with the real event types. TASK-0579 owns the rename pass across the catalogue. This task fixes the lore section only.
- The codex authorization defect (w2-campaign-lore F1) belongs to the security theme. Do not change authorization here.
- `refined/0495-remove-backward-compatibility-shims-campaign-lore.md` removes shims. Do not change shim files here.

## Product & User Story References
- [`us-0036-rag-indexed-campaign-worldbuilding-lore.md`](../../user_stories/accepted/us-0036-rag-indexed-campaign-worldbuilding-lore.md)
- [`us-0050-collaborative-campaign-atlas-and-living-codex.md`](../../user_stories/accepted/us-0050-collaborative-campaign-atlas-and-living-codex.md)
- [`prd-0007-campaign-worldbuilding-lore-and-rag-engine.md`](../../product/accepted/prd-0007-campaign-worldbuilding-lore-and-rag-engine.md)

## Detailed Specification & Implementation Plan
1. Pass the configured bus into the lore repositories. Publish committed events on the topic names in the event-family mapping (see TASK-0565 for the repository rule).
2. Replace `_campaign_codex_entries` with a list query. Two acceptable approaches: a persisted codex index table fed by the repository publish path, or a stream query rebuilt at start-up. Choose one and document it.
3. Rebuild retrieval state (documents, graph, vector and chunk stores) from `LoreDocumentAggregate` events on start-up. Delete `_documents` as source of truth.
4. Keep the RAG backend interface. The in-memory vector store remains a test double only, selected by configuration, not by default in deployment (the backend choice is in TASK-0448 and TASK-0469).
5. Atlas read: remove the broad `except` (see TASK-0561).

## Frontdoor Blackbox Test Plan
- **Fail before, pass after:** ingest a lore document through the public route, restart the app, run a search through the public route. Before: no results. After: the document is returned.
- **Fail before, pass after:** publish a codex entry, restart, list codex entries. Before: empty. After: the entry is listed.
- **Fail before, pass after:** ingest a document, then read the events-stream topic `runefoble.events.lore.document_ingested` through the stream reader. Before: no entry. After: one entry.
- Public routes and stream only.

## Definition of Done
1. Lore repositories publish committed events. Codex list and retrieval state rebuilt from events.
2. Three tests above pass.
3. Events-schema lore section and how-to corrected.
4. `uv run pytest` and `make health-check` pass. Files under 500 lines.
5. `CHANGELOG.md` entry.
