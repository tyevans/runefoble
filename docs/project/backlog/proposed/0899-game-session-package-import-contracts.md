---
id: '0899'
title: game_session Package Import Contracts Are Enforced (ADR-0021 Step 5)
status: Proposed
created: 2026-11-19
dependencies:
- '0898'
governing_adrs:
- ADR-0021
- ADR-0015
governing_prds: []
governing_stories: []
target_bc: game_session
target_release: 0.9.0
---

# TASK-0899: game_session Package Import Contracts Are Enforced (ADR-0021 Step 5)

## Status

Proposed.

## Summary

Add `import-linter` contracts that forbid imports between game_session domain packages, and update the docs rows.

## Problem Statement

- ADR-0021 D4 rule 9.

## Documentation & Architecture Review

- [ADR-0021](../../adrs/accepted/adr-0021-game-session-internal-bounded-contexts.md): game_session packages, ports-only import rule, migration order (D7).
- ADR-0015: no substitute values, no shims (DoR 9).

## Product & User Story References

None. Internal structure or data integrity.

## Detailed Specification & Implementation Plan

1. Add `independence` or `forbidden` contracts in `pyproject.toml` `[tool.importlinter]` for the five packages, and a contract that `game_session.shared` imports no domain package.
2. Update the `game_session` rows in AGENTS.md and `docs/reference/architecture-overview.md`, and the paths in `docs/reference/game-session-child-indexes.md`.

## Frontdoor Blackbox Test Plan

- `uv run lint-imports` passes. A test import between two domain packages makes it fail (check by hand, do not commit the bad import).

## Definition of Done

- The plan is done. All game_session blackbox suites stay green. Docs updated. CHANGELOG entry.

## Audit Provenance

- Severity: low
- Source audits: .audit/work/0753.md
