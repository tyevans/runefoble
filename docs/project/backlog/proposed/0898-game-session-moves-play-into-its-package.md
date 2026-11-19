---
id: '0898'
title: game_session Moves the play Domain Into Its Package (ADR-0021 Step 4)
status: Proposed
created: 2026-11-19
dependencies:
- '0897'
- '0754'
governing_adrs:
- ADR-0021
- ADR-0015
governing_prds: []
governing_stories: []
target_bc: game_session
target_release: 0.9.0
---

# TASK-0898: game_session Moves the play Domain Into Its Package (ADR-0021 Step 4)

## Status

Proposed.

## Summary

Move the modules that ADR-0021 D2 gives to `play` into `game_session/play/`. This is the last package move.

## Problem Statement

- ADR-0021 D2 lists the modules of `play`.

## Documentation & Architecture Review

- [ADR-0021](../../adrs/accepted/adr-0021-game-session-internal-bounded-contexts.md): game_session packages, ports-only import rule, migration order (D7).
- ADR-0015: no substitute values, no shims (DoR 9).

## Product & User Story References

None. Internal structure or data integrity.

## Detailed Specification & Implementation Plan

1. Move the modules and update every import in the same commit. No re-exports.
2. Schedule this task alone.

## Frontdoor Blackbox Test Plan

- All game_session blackbox suites pass with unchanged routes.

## Definition of Done

- The plan is done. All game_session blackbox suites stay green. Docs updated. CHANGELOG entry.

## Audit Provenance

- Severity: low
- Source audits: .audit/work/0753.md
