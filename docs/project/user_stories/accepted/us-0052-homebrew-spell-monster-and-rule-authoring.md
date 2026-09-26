---
id: 0052
title: Homebrew Spell, Monster & Rule Template Authoring
persona: Alex (Developer)
status: Accepted
created: 2026-09-26
governing_prd: PRD-0008
---

# US-0052 — Homebrew Spell, Monster & Rule Template Authoring

## Governing PRD
- [`PRD-0008: TTRPG Rules Compendium & Automated Encounter Builder`](../../product/accepted/prd-0008-ttrpg-rules-compendium-and-encounter-builder.md)

## Persona
Alex (Developer) / Evelyn (DM)

## User Story

**As a** creative Dungeon Master or homebrew creator running custom rule systems,  
**I want to** define custom monsters, spells, and action economy rules through validated JSON schemas and index them into `rules_compendium`,  
**So that** my bespoke creatures and spells seamlessly integrate with automated CR balancing, FastMCP lookups, and The Watcher's combat arbitration.

## Acceptance Criteria

1. **Schema-Validated Ingestion**: Custom monsters and spells are validated against strict Pydantic schemas (stat block, traits, legendary actions, spell components).
2. **SpiceDB Campaign Isolation**: Homebrew rules are scoped to the creating campaign via Zanzibar object permissions (`campaign:id#member`), remaining private unless explicitly published to the group.
3. **Hybrid Search Indexing**: Newly registered homebrew entries are dynamically indexed into `redstring` BM25 lexical and vector stores within 50ms.
4. **FastMCP Exposition**: The Watcher and autonomous agent tools can immediately query and apply homebrew stat blocks during tactical encounters.
