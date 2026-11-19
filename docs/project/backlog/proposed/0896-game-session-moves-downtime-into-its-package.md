---
id: '0896'
title: game_session Moves the downtime Domain Into Its Package (ADR-0021 Step 4)
status: Proposed
created: 2026-11-19
dependencies:
- '0895'
governing_adrs:
- ADR-0021
- ADR-0015
governing_prds: []
governing_stories: []
target_bc: game_session
target_release: 0.9.0
---

# TASK-0896: game_session Moves the downtime Domain Into Its Package (ADR-0021 Step 4)

## Status

Proposed.

## Summary

Move the modules that ADR-0021 D2 gives to `downtime` into `game_session/downtime/`. It adds the `SessionRoster` port.

## Problem Statement

- ADR-0021 D2 lists the modules of `downtime`. They are in the flat layout today.

## Documentation & Architecture Review

- [ADR-0021](../../adrs/accepted/adr-0021-game-session-internal-bounded-contexts.md): game_session packages, ports-only import rule, migration order (D7).
- ADR-0015: no substitute values, no shims (DoR 9).

## Product & User Story References

None. Internal structure or data integrity.

## Detailed Specification & Implementation Plan

1. Move the modules. Update the imports of code, tests and docs in the same commit. No re-exports.
2. Cross-package needs go through ports in `<package>/ports.py` (ADR-0021 D4).
3. Schedule this task alone: it conflicts with other game_session work.

## Frontdoor Blackbox Test Plan

- All game_session blackbox suites pass with unchanged routes (ADR-0021 D5).

## Definition of Done

- The plan is done. All game_session blackbox suites stay green. Docs updated. CHANGELOG entry.

## Audit Provenance

- Severity: low
- Source audits: .audit/work/0753.md
