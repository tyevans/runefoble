---
id: 0008
title: TTRPG Rules Compendium & Automated Encounter Builder
status: Shipped
created: 2026-09-25
---

# PRD-0008 — TTRPG Rules Compendium & Automated Encounter Builder

## Who this is for

Overworked Dungeon Masters (Evelyn) preparing combat encounters, players checking spell details, and developers (Alex) building custom homebrew rule systems.

## What the person cannot do today

Currently, encounter preparation requires flipping through rulebooks, computing Challenge Rating (CR) XP budgets manually, and hand-copying monster stat blocks. In-game rule questions frequently stall combat for minutes at a time.

## What good looks like

- **Structured System Rules Compendium**: Queryable, versioned database of SRD/ORC monsters, spells, items, feats, conditions, and action economy rules indexed via `redstring` (`tyevans/redstring`).
- **BM25 & Semantic Rule Search**: Instant hybrid retrieval allowing natural language queries ("spells that cause blindness with a CON save") resolved through `redstring` BM25 lexical search and vector embeddings.
- **Automated CR Balancing Engine**: The DM specifies party composition and target encounter lethality (Trivial, Moderate, Deadly), and the engine generates synergistic enemy groups with balanced action economy.
- **Homebrew Extensibility**: Developers and DMs can define custom spells, traits, and creatures that directly interface with tactical combat rules and The Watcher's arbitration.

## What this does not do

- It does not infringe on copyrighted non-SRD commercial game content (strictly uses SRD 5.1, ORC, or user homebrew).
- It does not force rigid encounter constraints; DMs can manually tune and override any encounter parameters.

## What it costs at scale

Low-latency index caching in Redis is required to keep compendium searches sub-50ms during live voice gameplay.

## Checkable Outcomes

1. Compendium API powered by `redstring` returns structured stat blocks, spell definitions, and condition mechanics under 50ms.
2. Encounter builder calculates CR difficulty thresholds for arbitrary party sizes and levels.
3. Custom homebrew rules can be registered and surfaced through FastMCP tools and The Watcher intent validator.

## Linked User Stories
- [`US-0034: Agnostic TTRPG Ruleset Schemas and System Expansion`](../../user_stories/accepted/us-0034-agnostic-ttrpg-ruleset-schemas-and-system-expansion.md)
- [`US-0037: Automated CR Encounter Balancing & redstring Rules Indexing`](../../user_stories/accepted/us-0037-automated-cr-encounter-balancing-and-compendium.md)
- [`US-0052: Homebrew Spell, Monster & Rule Template Authoring`](../../user_stories/accepted/us-0052-homebrew-spell-monster-and-rule-authoring.md)

## Implementing Backlog Tasks
- [`TASK-0048: TTRPG Rules Compendium & Automated Encounter Builder Microservice`](../../backlog/complete/0048-rules-compendium-and-encounter-builder-bc.md)
- [`TASK-0108: Rules Compendium Search & Encounter Builder Microfrontend`](../../backlog/refined/0108-rules-compendium-search-and-encounter-builder-microfrontend.md)
