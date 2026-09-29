---
id: '0499'
title: Remove Backward Compatibility Shims & Re-exports in audience_studio
status: Refined
created: 2026-09-29
dependencies:
- TASK-0014
- TASK-0439
governing_adrs:
- ADR-0003
- ADR-0013
- ADR-0014
governing_prds:
- PRD-0011
governing_stories:
- US-0014
- US-0043
target_release: 0.9.0
---

# TASK-0499: Remove Backward Compatibility Shims & Re-exports in audience_studio

## Status
Refined

## Summary
Excise legacy poll option wrappers, deprecated voting payload shims, and transitional re-export facades from `services/audience_studio`, standardizing on canonical TypeScript event schemas and microfrontend contracts.

## Problem Statement
`services/audience_studio` is a TypeScript microservice powering live audience chaos polls and spectator interaction. During integration with the Gateway (`TASK-0439`) and App Shell (`TASK-0440`), transitional payload wrappers and legacy poll option schemas were introduced to handle prototype voting messages. With zero live external users, these transitional shims introduce dead branches and violate the DoR zero backward compatibility policy.

## Documentation & Architecture Review
- **Documentation Consulted**:
  - `docs/how-to/orchestrate-audience-chaos-polls.md`: Audience chaos polls and voting pipelines.
  - `docs/reference/ports-and-endpoints.md`: Audience studio port 8011.
- **Governing Architecture & ADRs**:
  - **ADR-0013: Frontend Microfrontend Architecture**: Microfrontend UI package vendoring.
  - **ADR-0014: Behavior-Driven Development and Playwright E2E**: Frontdoor testing.

## Product & User Story References
- [`prd-0011-live-audience-chaos-studio-and-spectator-overlay.md`](../../product/accepted/prd-0011-live-audience-chaos-studio-and-spectator-overlay.md)
- [`us-0014-real-time-spectator-clean-overlay.md`](../../user_stories/accepted/us-0014-real-time-spectator-clean-overlay.md)
- [`us-0043-audience-chaos-polls-and-voting.md`](../../user_stories/accepted/us-0043-audience-chaos-polls-and-voting.md)

## Detailed Specification & Implementation Plan
1. **Remove Legacy Voting Payload Shims**:
   - In `services/audience_studio/src/types/`, remove deprecated voting payload interfaces and legacy option converters.
   - Standardize all poll creation, voting, and DM approval handlers on canonical schemas.
2. **Prune Re-export Facades**:
   - In `services/audience_studio/src/index.ts`, ensure only authoritative classes and types are exported without legacy aliases.
3. **Clean Up Microfrontend Contracts**:
   - In `services/audience_studio/ui/src/`, verify `<runefoble-audience-studio>` consumes authoritative event interfaces directly without backward-compatibility adapters.
4. **Update Blackbox and BDD Tests**:
   - Verify tests in `tests/test_blackbox_audience_studio*` pass against canonical schemas.

## INVEST Criteria Evaluation
- **Independent (I)**: Self-contained within `services/audience_studio`.
- **Negotiable (N)**: Clean TypeScript type definitions.
- **Valuable (V)**: Prevents schema drift in live streaming and audience voting modules.
- **Estimable (E)**: Clearly bounded to TypeScript models and index exports.
- **Small (S)**: File changes well under 50 lines.
- **Testable (T)**: Verified via `pnpm test` and pytest blackbox suites.

## Definition of Done
1. Deprecated voting payload interfaces and shims removed.
2. Index re-exports pruned of legacy aliases.
3. Microfrontend and backend synchronized on canonical schemas.
4. All audience studio tests and typechecks pass.
