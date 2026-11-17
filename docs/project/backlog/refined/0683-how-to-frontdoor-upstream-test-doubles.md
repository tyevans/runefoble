---
id: '0683'
title: How-To Guide for Frontdoor Upstream Test Services
status: Refined
created: 2026-11-17
dependencies: []
governing_adrs:
- ADR-0014
governing_prds: []
governing_stories: []
target_release: 0.9.0
severity: low
source_audits:
- work/0603.md
- work/0606.md
---

# TASK-0683: How-To Guide for Frontdoor Upstream Test Services

## Status
Refined. Consolidation approved by the user at the round-10 pause (2026-11-17).

## Summary
`tests/helpers/live_services.py` (`serve`, `unavailable_app`, `closed_port_url`) runs real service apps on loopback ports so gateway and MCP tests call them over HTTP. This is now the standard frontdoor pattern for cross-service tests, but it is not documented. Workers write their own variants.

## Problem Statement
- TASK-0603 added the helper. TASK-0606 and later tasks reuse it. Other tests still monkeypatch clients or use ad hoc stubs.
- AGENTS.md: generic, reusable patterns need a Diataxis how-to.

## Documentation & Architecture Review
- ADR-0014 (frontdoor setup, no backdoors). `docs/how-to/validate-e2e-journeys-with-playwright-bdd.md` covers browser tests only.

## Product & User Story References
None. Developer documentation.

## Detailed Specification & Implementation Plan
1. Write `docs/how-to/test-cross-service-calls-with-live-upstreams.md`: when to use each helper, how to set the upstream URL setting, how to simulate 503 and an unreachable upstream, and what not to do (no monkeypatch of the code under test).
2. Add the guide to the AGENTS.md how-to index.
3. Find tests that stub upstream HTTP with monkeypatch of internal clients (`grep -rn "monkeypatch.setattr(.*client" tests/`). List them in the guide's "Known gaps" section or fix up to 3 small ones.

## Frontdoor Blackbox Test Plan
- Any test migrated in step 3 fails before (if the client were broken) and passes after, through HTTP only.

## Definition of Done
- Guide written and indexed. CHANGELOG line given to the orchestrator.
