---
id: '0615'
title: Asset Forge Wardrobe Synthesis Behind a Generator Port With Accurate Face Claims
status: Complete
created: 2026-11-17
dependencies: []
governing_adrs:
- ADR-0003
- ADR-0007
- ADR-0014
governing_prds:
- PRD-0009
governing_stories:
- US-0055
target_release: 0.9.0
severity: high
source_audits:
- w2-asset-forge.md
---

# TASK-0615: Asset Forge Wardrobe Synthesis Behind a Generator Port With Accurate Face Claims

## Status
Complete

## Summary
The wardrobe portrait variant draws a flat colour disk for the face and a flat colour fill for attire. The attire prompt is built and returned but never used to make the image. The docs say the variant "preserves face embeddings". This task puts the image synthesis behind a `WardrobeGenerator` port, with the deterministic placeholder as the named default, and makes the route and docs state what is produced.

## Problem Statement
- `services/asset_forge/src/asset_forge/raster/wardrobe_raster.py` `generate_wardrobe_portrait_png`: face is a disk coloured from a SHA-256 of `face_seed` or `character_name`. Attire is a fixed-palette fill with a sine fold.
- No model, embedding or image input is used. `ATTIRE_PROMPTS` text is returned as `prompt` and not used.
- `docs/reference/ports-and-endpoints.md` line 198 and `docs/how-to/manage-generative-wardrobe-and-condition-portraits.md` say the variant preserves face embeddings. That is false.

Source: `.audit/reports/w2-asset-forge.md` F5.

## Documentation & Architecture Review
- ADR-0014: the wardrobe how-to must match the blackbox tests.
- `docs/project/user_stories/accepted/us-0055-dynamic-character-wardrobe-and-condition-portraits.md` describes the user value.
- TASK-0444 and TASK-0445 (refined, wardrobe proxy and App Shell) depend on the route shape. Keep the route path and fields stable.

## Product & User Story References
- `docs/project/product/accepted/prd-0009-procedural-battlemap-and-token-asset-generation.md`
- `docs/project/user_stories/accepted/us-0055-dynamic-character-wardrobe-and-condition-portraits.md`

## Detailed Specification & Implementation Plan
1. Define `WardrobeGenerator` Protocol: `generate(portrait, attire_prompt, face_seed) -> PngBytes`.
2. Move the current logic into `PlaceholderWardrobeGenerator`. Its docs state it draws a placeholder and preserves no face.
3. The route response includes `generator` and `preserves_face: false` for the placeholder.
4. Add a settings key for a configured generator. The attire prompt is passed to the configured generator.
5. Correct the two docs to match the placeholder default.

## Frontdoor Blackbox Test Plan
- Before fix: two wardrobe requests with different attire prompts produce the same image bytes (test fails for the "differs" assertion).
- After fix: the response reports `generator` and `preserves_face`. For the default, `preserves_face` is `false`.
- After fix: docs and the route response agree (a doc test checks the phrase "preserves face embeddings" is absent from the reference).

## Definition of Done
1. Generator port and placeholder default in place. Files under 500 lines.
2. Blackbox tests pass. `uv run pytest services/asset_forge` passes.
3. Ruff check and format pass.
4. Reference and how-to docs corrected. `CHANGELOG.md` `[Unreleased]` entry added.
