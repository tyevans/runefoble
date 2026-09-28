---
id: '0295'
title: Lore Domain Events Modular Decomposition
status: Proposed
created: 2026-09-28
dependencies:
- TASK-0047
- TASK-0101
- TASK-0106
governing_adrs:
- ADR-0002
- ADR-0006
- ADR-0007
- ADR-0013
governing_prds:
- PRD-0007
- PRD-0015
governing_stories:
- US-0036
- US-0045
- US-0050
target_release: 0.8.0
---

# TASK-0295: Lore Domain Events Modular Decomposition

## Status
Proposed

## Summary
Decompose `libs/runefoble_events/src/runefoble_events/lore.py` (299 lines, 59.8% of limit) into modular submodules under `libs/runefoble_events/src/runefoble_events/lore/` (`documents.py`, `handouts.py`, `atlas.py`, `codex.py`, `__init__.py`), ensuring all event submodules remain strictly < 100 lines per Hard Invariant 6.

## Problem Statement
`libs/runefoble_events/src/runefoble_events/lore.py` currently defines 15 distinct CloudEvents across four separate domain concerns in a single monolithic 299-line file:
1. Knowledge base document ingestion and entity extraction (`LoreDocumentIngested`, `EntitiesExtracted`, `AliasesConsolidated`)
2. Diegetic handouts, wax seals, and relics (`HandoutGenerated`, `WaxSealBroken`, `InvisibleInkRevealed`, `RelicForged`, `RelicInspected`, `RelicRuneTranslated`)
3. World atlas pins, layer toggles, and territory boundaries (`AtlasPinCreated`, `AtlasPinUpdated`, `AtlasLayerToggled`, `AtlasTerritoryUpdated`)
4. Living party codex entries (`CodexEntryPublished`, `CodexEntryUpdated`)

As West Marches frontier maps, alchemical reagent lore, and secret GM handouts expand, this event catalog will quickly breach Hard Invariant 6 (<500 lines) unless modularized.

## Governing Architecture & ADRs
- **ADR-0002: CloudEvents 1.0 Domain Events via eventsource-py**: Standardizes `@register_event` and `BaseRunefobleEvent` event schemas.
- **ADR-0006: Redis Streams Event Bus Transport**: Ensures consistent event type names across streams.
- **ADR-0007: Domain-Driven Design Context Boundaries**: Separates knowledge base, atlas, codex, and tactile relics into cohesive event boundaries.
- **ADR-0013: Modular Decomposition**: All source files kept strictly < 500 lines (submodules < 100 lines).

## Scope of Work
1. **Document & Entity Events (`libs/runefoble_events/src/runefoble_events/lore/documents.py`)**:
   - Extract `LoreDocumentIngested`, `EntitiesExtracted`, and `AliasesConsolidated` (< 80 lines).
2. **Tactile Handouts & Relics Events (`libs/runefoble_events/src/runefoble_events/lore/handouts.py`)**:
   - Extract `HandoutGenerated`, `WaxSealBroken`, `InvisibleInkRevealed`, `RelicForged`, `RelicInspected`, and `RelicRuneTranslated` (< 90 lines).
3. **Atlas Events (`libs/runefoble_events/src/runefoble_events/lore/atlas.py`)**:
   - Extract `AtlasPinCreated`, `AtlasPinUpdated`, `AtlasLayerToggled`, and `AtlasTerritoryUpdated` (< 80 lines).
4. **Codex Events (`libs/runefoble_events/src/runefoble_events/lore/codex.py`)**:
   - Extract `CodexEntryPublished` and `CodexEntryUpdated` (< 60 lines).
5. **Re-export Facade (`libs/runefoble_events/src/runefoble_events/lore/__init__.py`)**:
   - Re-export all 15 event classes to maintain 100% backwards compatibility with existing consumers and `runefoble_events.events`.
6. **Verification**:
   - Run `uv run pytest` across the test suite to ensure all event registrations and serialization remain intact.

## Definition of Done
- `libs/runefoble_events/src/runefoble_events/lore.py` replaced by `libs/runefoble_events/src/runefoble_events/lore/` package.
- All extracted event submodules strictly < 100 lines per Hard Invariant 6.
- 100% backwards compatibility preserved through `runefoble_events.lore` and `runefoble_events.events`.
- All domain event registration and serialization tests pass cleanly.
