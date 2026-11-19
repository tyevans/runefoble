---
id: '0892'
title: "ADR Spike: Decide Whether to Merge the Two Merchant Models"
status: Proposed
created: 2026-11-19
dependencies: []
governing_adrs:
- ADR-0021
- ADR-0015
governing_prds: []
governing_stories: []
target_bc: game_session
target_release: 0.9.0
---

# TASK-0892: ADR Spike: Decide Whether to Merge the Two Merchant Models

## Status

Proposed.

## Summary

game_session has two merchant models: `MerchantAggregate` (`merchants.py`, PRD-0014, `downtime`) and `NegotiationAggregate` (`settlement/haggling/`, PRD-0024, `settlement`). Write an ADR that decides whether to merge them or keep them separate.

## Problem Statement

- ADR-0021 Consequences, Neutral: the ADR does not merge them. The user asked for a spike (2026-11-19).

## Documentation & Architecture Review

- [ADR-0021](../../adrs/accepted/adr-0021-game-session-internal-bounded-contexts.md): game_session packages, ports-only import rule, migration order (D7).
- ADR-0015: no substitute values, no shims (DoR 9).

## Product & User Story References

None. Internal structure or data integrity.

## Detailed Specification & Implementation Plan

1. Compare the state, events and routes of both models.
2. Write the ADR with options, decision and migration if a merge is chosen.

## Frontdoor Blackbox Test Plan

None (documentation spike). `spec-ops health` passes.

## Definition of Done

- The plan is done. All game_session blackbox suites stay green. Docs updated. CHANGELOG entry.

## Audit Provenance

- Severity: low
- Source audits: .audit/work/0753.md
