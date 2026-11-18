---
id: '0616'
title: Rules Compendium Semantic Search Uses a Configured Embedding Provider
status: Complete
created: 2026-11-17
dependencies: []
governing_adrs:
- ADR-0003
- ADR-0007
- ADR-0014
governing_prds:
- PRD-0008
governing_stories:
- US-0037
target_release: 0.9.0
---

# TASK-0616: Rules Compendium Semantic Search Uses a Configured Embedding Provider

## Status
Complete

## Summary
The "semantic" half of rules search uses redstring's `FakeEmbeddingProvider`, which derives vectors from a hash of the text. The service and its README say "semantic vector retrieval". This task adds a configured embedding port with a real default. The fake stays only in tests. Docs state the retrieval mode the service actually uses.

## Problem Statement
- `services/rules_compendium/src/.../retrieval.py:24` (removed): `self.embeddings = redstring.FakeEmbeddingProvider(dimension=dimension)`.
- redstring documents the fake as "deterministic unit vectors derived from a hash of the text".
- The lexical BM25 part is real.
- No real provider is wired and no toggle exists. `services/rules_compendium/README.md` and the module docstring claim semantic retrieval.

Source: `.audit/reports/w2-rules-compendium.md` F7.

## Documentation & Architecture Review
- `docs/how-to/balance-combat-encounters-and-query-compendium.md`: describes search. Update the retrieval modes.
- `docs/reference/platform-services.md`: add the embedding setting.
- TASK-0244 (proposed) decomposes the hybrid retrieval module. Coordinate: this task edits `retrieval.py` and TASK-0244 splits it. Prefer 0244 first, or merge the change into the new module.

## Product & User Story References
- `docs/project/product/accepted/prd-0008-ttrpg-rules-compendium-and-encounter-builder.md`
- `docs/project/user_stories/accepted/us-0037-automated-cr-encounter-balancing-and-compendium.md`

## Detailed Specification & Implementation Plan
1. Add `rules_compendium.embedding` setting: `lexical` (BM25 only, explicit), or a configured provider name.
2. Build the embedding provider in a factory from settings. Remove the `FakeEmbeddingProvider` default.
3. Search responses include `retrieval_mode` (`lexical` or `hybrid`).
4. Fix README and docstring to match.

## Frontdoor Blackbox Test Plan
- Before fix: search with a paraphrase query returns results only from the hash vector (test fails when the expected semantic match is absent in lexical mode, and the response claims hybrid).
- After fix: the response reports `retrieval_mode`. Default mode is `lexical` unless a provider is configured.
- After fix: with the test embedding provider configured through settings, a paraphrase query returns the expected rule.

## Definition of Done
1. No fake embedding provider constructed in production code.
2. Factory and setting in place. Files under 500 lines.
3. Blackbox tests pass. `uv run pytest services/rules_compendium` passes.
4. Ruff check and format pass.
5. README and docs corrected. `CHANGELOG.md` `[Unreleased]` entry added.

## Audit Provenance

- Severity: medium
- Source audits: `w2-rules-compendium.md`
