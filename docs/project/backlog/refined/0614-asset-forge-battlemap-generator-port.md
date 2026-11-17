---
id: '0614'
title: Asset Forge Battlemap Generator Behind a Configurable Port
status: Refined
created: 2026-11-17
dependencies: []
governing_adrs:
- ADR-0003
- ADR-0007
- ADR-0014
governing_prds:
- PRD-0009
governing_stories:
- US-0038
target_release: 0.9.0
severity: medium
source_audits:
- w2-asset-forge.md
---

# TASK-0614: Asset Forge Battlemap Generator Behind a Configurable Port

## Status
Refined

## Summary
Battlemap "generation" is keyword matching plus a seeded grid. The prompt changes only the theme label, not the layout. This task puts layout and raster generation behind a `MapGenerator` port. The deterministic generator stays as the explicit default, and it is documented as such. A configured provider can replace it.

## Problem Statement
- `services/asset_forge/src/asset_forge/geometry.py`: `infer_theme_from_prompt` (keyword lists) and `generate_map_layout` (fixed divider walls; pillars from `(x*7 + y*13 + seed) % 10`).
- `raster/battlemap_raster.py` draws flat colours.
- Probe: a crypt prompt yields theme `crypt` and 9 walls. Any prompt of the same size gives the same layout shape.
- AGENTS.md describes "procedural battlemap diffusion synthesis". The code has no generator interface.

Source: `.audit/reports/w2-asset-forge.md` F6.

## Documentation & Architecture Review
- `docs/how-to/forge-procedural-battlemaps-and-tokens.md`: must say what the default does.
- `AGENTS.md` repository table: the diffusion wording must match the default unless a provider is configured. Correct it in the same change.
- ADR-0007: generator is an adapter behind a domain port.

## Product & User Story References
- `docs/project/product/accepted/prd-0009-procedural-battlemap-and-token-asset-generation.md`
- `docs/project/user_stories/accepted/us-0038-generative-procedural-battlemaps-and-tokens.md`

## Detailed Specification & Implementation Plan
1. Define `MapGenerator` Protocol: `generate(prompt, width, height, seed) -> MapLayout`.
2. Move the current logic into `DeterministicMapGenerator` (named as such, documented as the default).
3. Add settings `asset_forge.map_generator` (default `deterministic`). A configured external provider implements the same protocol.
4. Keep raster code behind the layout output.
5. Remove the claim of diffusion from docs and AGENTS.md, or add the provider that does it.

## Frontdoor Blackbox Test Plan
- Before fix: two battlemap requests with different prompts and the same size and seed return the same wall layout (test fails for the "differs" assertion).
- After fix: the two prompts produce different layouts through the deterministic generator, because the prompt is part of the generator input.
- After fix: the response names the generator used.

## Definition of Done
1. Generator port and default implementation in place. Files under 500 lines.
2. Blackbox tests pass. `uv run pytest services/asset_forge` passes.
3. Ruff check and format pass.
4. AGENTS.md and forge how-to corrected. `CHANGELOG.md` `[Unreleased]` entry added.
