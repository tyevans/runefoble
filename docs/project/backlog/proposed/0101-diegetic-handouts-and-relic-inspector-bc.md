---
id: '0101'
title: Generative Diegetic Handouts, Wax Seals & 3D Relic Inspector
status: Proposed
created: 2026-09-26
dependencies:
- TASK-0023
- TASK-0047
- TASK-0049
governing_adrs:
- ADR-0003
- ADR-0006
- ADR-0010
- ADR-0013
target_release: 0.4.0
prd_url: docs/project/product/accepted/prd-0015-generative-handouts-relic-inspector-and-printable-forge.md
user_story: US-0045
---

# TASK-0101: Generative Diegetic Handouts, Wax Seals & 3D Relic Inspector

## Status
Proposed

## Summary
Build an in-world diegetic artifact generation pipeline and interactive WebGL relic inspector, providing weathered letters with breakable wax seals, hidden runes, and rotating 3D magical items.

## Problem Statement
Finding fantasy clues or magical artifacts is currently limited to plain text modals or flat static PNG images (PRD-0015, US-0045). Chroniclers and players like Rowan need tactile artifacts they can interact with, unseal with sound effects, and rotate in 3D to inspect hidden inscriptions and runes.

## Governing Architecture & ADRs
- **ADR-0003**: UV Monorepo Workspace (`services/campaign_lore` and `services/asset_forge`).
- **ADR-0006**: Redis Streams Event Bus (`HandoutGenerated`, `WaxSealBroken`, `RelicInspected`).
- **ADR-0010**: OpenTelemetry Distributed Tracing & Metrics.
- **ADR-0013**: Microfrontend Architecture and Service Component Vendoring (`<runefoble-relic-inspector>` and `<runefoble-handout-viewer>`).

## Scope of Work
1. **Generative Diegetic Handout Engine**:
   - Synthesizer generating weathered parchment textures, stylized calligraphy, and wax seal graphics.
   - UV-reactive invisible ink layer revealed under simulated torchlight cursor.
2. **Breakable Wax Seal Physics & Audio**:
   - Dynamic stamp cracking animation and haptic audio synthesis upon interaction.
3. **Interactive 3D WebGL Relic Inspector**:
   - Three.js/WebGL canvas component with orbit controls, metallic shaders, and clickable rune hitboxes.
4. **Microfrontend Components & Storybook**:
   - Web components vendored under `services/campaign_lore/ui/src/`.
5. **Frontdoor Blackbox Verification**:
   - Blackbox test suite verifying artifact generation, seal states, and 3D asset metadata.
