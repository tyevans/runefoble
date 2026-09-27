---
id: '0124'
title: Generative Character Wardrobe, Emotion & State Portrait Gallery
status: Refined
created: 2026-09-26
dependencies:
- TASK-0009
- TASK-0023
- TASK-0049
governing_adrs:
- ADR-0003
- ADR-0006
- ADR-0013
governing_prds:
- PRD-0016
governing_stories:
- US-0055
target_release: 0.4.0
---

# TASK-0124: Generative Character Wardrobe, Emotion & State Portrait Gallery

## Status
Refined

## Summary
Build dynamic character portrait variant synthesis and condition overlays, adapting character avatars and board tokens in real-time to current HP thresholds (<50% bloodied), condition afflictions, and generative narrative wardrobe changes (ballroom masquerade, arctic tundra).

## Problem Statement
Player avatars currently remain static 2D icons throughout an entire campaign regardless of injury, status effects, or disguised narrative attire (PRD-0016, US-0055). Performers like Nadia need portraits and tokens that reflect low-HP bloodied states and seasonal outfit variants without manual Photoshop editing.

## Governing Architecture & ADRs
- **ADR-0003: UV Monorepo Workspace for Python BCs**: Domain logic in `services/character_sheet/` and `services/asset_forge/`.
- **ADR-0006: Redis Streams Event Bus**: Event dispatch for `CharacterConditionApplied`, `CharacterDamaged`, and `PortraitVariantGenerated`.
- **ADR-0013: Microfrontend Architecture and Service Component Vendoring**: Avatar gallery component in `services/character_sheet/ui/src/`.

## Product & User Story References
- **Product Requirement**: [`prd-0016-character-leitmotifs-and-kinetic-spell-vfx.md`](../../product/accepted/prd-0016-character-leitmotifs-and-kinetic-spell-vfx.md)
- **User Story**: [`us-0055-dynamic-character-wardrobe-and-condition-portraits.md`](../../user_stories/accepted/us-0055-dynamic-character-wardrobe-and-condition-portraits.md)

## Detailed Specification & Implementation Plan
1. **Condition & Injury Overlay Engine (`services/character_sheet/src/character_sheet/portrait.py`)**:
   - Dynamic SVG/Canvas composition applying bloodied vignettes, poisoned auras, and stunned dizzy icons over base portraits.
   - Real-time resolution on character HP transitions (< 50% HP triggers bloodied badge).
2. **Generative Wardrobe Synthesis**:
   - `services/asset_forge/` prompt template generating stylized attire variations preserving character face embeddings.
   - S3 storage in Silo with signed CDN URLs.
3. **Microfrontend Wardrobe Gallery Widget (`services/character_sheet/ui/src/runefoble-wardrobe-gallery.ts`)**:
   - Visual carousel of unlocked outfits and one-click active token portrait assignment.
4. **Frontdoor Blackbox Verification**:
   - Blackbox test suite verifying condition overlay rendering, asset storage metadata, and board token synchronization.

## INVEST Criteria Evaluation
- **Independent (I)**: Operates on character portraits without modifying combat resolution logic.
- **Negotiable (N)**: Preset CSS overlays vs server-side composited WebP variants.
- **Valuable (V)**: Elevates immersion by visually representing wounds and narrative attire.
- **Estimable (E)**: Leverages existing Silo S3 uploader and character sheet REST APIs.
- **Small (S)**: Scope strictly isolated to `services/character_sheet/` and `services/asset_forge/`; all files < 300 lines.
- **Testable (T)**: Frontdoor tests verify avatar URLs and condition overlay triggers.

## Definition of Done (Hard Invariant 7: Blackbox TDD with Frontdoor Setup)
1. **Dynamic Condition Overlays**:
   - Character sheet REST API returns updated active portrait URL and condition badges upon HP drop below 50%.
2. **Microfrontend Element**:
   - `<runefoble-wardrobe-gallery>` rendered with Shadow DOM and Bauhaus tokens.
3. **Storybook Stories**:
   - Stories showcasing healthy, bloodied, poisoned, and gala attire portraits.
4. **Frontdoor Blackbox Test Suite**:
   - `tests/test_blackbox_wardrobe_gallery.py` verifying portrait variant generation and event dispatch via public endpoints.
5. **Quality Gates**:
   - Conforms to Hard Invariant 6 (< 500 lines per file).
   - Passes `pnpm run build` and `uv run pytest tests/test_blackbox_wardrobe_gallery.py`.
