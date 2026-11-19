---
id: '0880'
title: Campaign Analytics Token Verifier Uses the Settings Passed to create_app
status: Complete
created: 2026-11-18
dependencies:
- TASK-0873
governing_adrs:
- ADR-0015
governing_prds:
- PRD-0023
governing_stories:
- US-0065
target_release: 0.9.0
---

# TASK-0880: Campaign Analytics Token Verifier Uses the Settings Passed to create_app

## Status
Complete

Source: TASK-0873 report (`.audit/work/0873.md`).

## Summary
`create_app(settings, event_bus)` builds Campaign Analytics from explicit settings (TASK-0873). The token verifier still comes from a module-level `platform_settings` read from the environment (`services/campaign_analytics/src/campaign_analytics/dependencies.py`, lines 22 and 56). So settings passed to `create_app` do not reach token verification. Build the verifier from the settings that `create_app` receives, and store it on the app.

## Product & User Story References
- [`prd-0023-unified-frontend-application-shell-and-campaign-hub.md`](../../product/accepted/prd-0023-unified-frontend-application-shell-and-campaign-hub.md)

## Detailed Specification & Implementation Plan
1. `create_app` builds the token verifier from its `settings` and keeps it in `app.state`.
2. The route dependencies read the verifier from the request app. The module-level `platform_settings` goes.
3. Update `docs/how-to/verify-identity-in-fastapi-and-websockets.md` if it names the module setting.

## Frontdoor Test Plan
Two apps built with `create_app` and two different issuer settings: each accepts a token from its own issuer and refuses a token from the other issuer (401).

## INVEST Criteria Evaluation
Small. Testable through HTTP routes.

## Definition of Done
1. The test passes. 2. No module-level settings in `dependencies.py`. 3. `make health-check` passes.
