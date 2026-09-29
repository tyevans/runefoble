---
id: '0468'
title: App Shell Campaign Lore Document Uploader and Alias Manager Microfrontend
status: Proposed
created: 2026-09-29
dependencies:
- TASK-0047
- TASK-0209
- TASK-0355
- TASK-0467
governing_adrs:
- ADR-0004
- ADR-0012
- ADR-0013
governing_prds:
- PRD-0007
- PRD-0023
governing_stories:
- US-0036
- US-0067
target_release: 0.9.0
---

# TASK-0468: App Shell Campaign Lore Document Uploader and Alias Manager Microfrontend

## Status
Proposed

## Summary
Implement the `runefoble-lore-document-uploader` and `runefoble-alias-manager` Lit Web Components in `services/campaign_lore/ui/src/` and integrate them into the Campaign Hub Codex subview in `frontend/src/runefoble-app.ts`. Enables Dungeon Masters to upload or paste Markdown worldbuilding lore, set DM secrecy flags (`is_secret`), tag entries, review automatically extracted entity nodes, and merge entity aliases into canonical graph nodes using Bauhaus design tokens and Storybook stories.

## Problem Statement
Currently, the Campaign Hub Codex view only displays read-only lore entries. Dungeon Masters have no interactive UI frontdoor to ingest new worldbuilding documents, configure document visibility, review extracted knowledge graph entities/relationships, or merge alias clusters without manually crafting raw backend HTTP requests.

## Governing Architecture & ADRs
- **ADR-0004: Lit Web Components and Storybook UI**: Encapsulated Shadow DOM components built in Storybook first.
- **ADR-0012: Theme Mode & Color Tokens**: Bauhaus design tokens for dark/light themes, form fields, and status indicators.
- **ADR-0013: Frontend Microfrontend Architecture**: Exported components from `services/campaign_lore/ui/` composed into the App Shell.

## Product & User Story References
- [`prd-0007-campaign-worldbuilding-lore-and-rag-engine.md`](../../product/accepted/prd-0007-campaign-worldbuilding-lore-and-rag-engine.md)
- [`prd-0023-unified-frontend-application-shell-and-campaign-hub.md`](../../product/accepted/prd-0023-unified-frontend-application-shell-and-campaign-hub.md)
- [`us-0036-rag-indexed-campaign-worldbuilding-lore.md`](../../user_stories/accepted/us-0036-rag-indexed-campaign-worldbuilding-lore.md)
- [`us-0067-campaign-detail-view-and-session-scheduling.md`](../../user_stories/accepted/us-0067-campaign-detail-view-and-session-scheduling.md)


## Scope of Work
1. **Document Uploader Component (`services/campaign_lore/ui/src/runefoble-lore-document-uploader.ts`)**:
   - Provide file dropzone / textarea input for Markdown or text worldbuilding lore.
   - Form controls: document title, tags, DM-only secrecy toggle (`is_secret`).
   - Dispatches `lore-document-ingested` event upon successful submission.
2. **Alias Manager Component (`services/campaign_lore/ui/src/runefoble-alias-manager.ts`)**:
   - Display list of discovered entity aliases.
   - Interactive merge drawer: select alias node, choose canonical entity node, and submit consolidation.
   - Dispatches `alias-consolidated` event upon completion.
3. **Storybook Stories**:
   - Create `runefoble-lore-document-uploader.stories.ts` and `runefoble-alias-manager.stories.ts` with interactive controls.
4. **App Shell Integration (`frontend/src/runefoble-app.ts`)**:
   - Mount uploader and alias manager modal inside Campaign Hub Codex tab when user has DM/Owner role.
   - Bind `AppDataService` methods to gateway lore endpoints with local fallback support.

## Definition of Done
1. Components implemented strictly < 250 lines each with Shadow DOM encapsulation.
2. Storybook stories render without errors and pass visual contrast checks.
3. Submitting a lore document triggers document ingestion via Gateway API or fallback cache.
4. Player view hides uploader and secret entries; DM view provides full management capabilities.
5. TypeScript builds cleanly with zero errors via `pnpm run build`.
