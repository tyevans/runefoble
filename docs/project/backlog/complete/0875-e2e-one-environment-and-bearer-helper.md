---
id: '0875'
title: E2E Suites Read One Environment Module and One Bearer Helper
status: Complete
created: 2026-11-18
dependencies: []
governing_adrs:
- ADR-0014
governing_prds: []
governing_stories: []
target_bc: frontend
target_release: 0.9.0
---
# TASK-0875: E2E Suites Read One Environment Module and One Bearer Helper

## Status
Complete

## Summary
The Playwright BDD support code repeats the API base URL, the Zitadel issuer, the audience and the `Authorization: Bearer` header. Put the environment values in one module and the header builder in one helper.

## Problem Statement
- `e2e/support/frontdoor_api.ts:32` defaults the API base to `http://localhost`.
- `e2e/steps/identity_negative_steps.ts:13-15` repeats the base URL. It reads `PLAYWRIGHT_ZITADEL_ISSUER` and `PLAYWRIGHT_ZITADEL_AUDIENCE` with defaults.
- `e2e/support/frontdoor_api.ts:37-39` and `e2e/steps/identity_negative_steps.ts:45` both build `Authorization: Bearer ${token}`.

## Documentation & Architecture Review
- ADR-0014 (Playwright BDD harness). `docs/reference/e2e-harness.md` lists the fixtures and environment variables. Update it.

## Product & User Story References
None. Test harness work.

## Detailed Specification & Implementation Plan
1. Add `e2e/support/env.ts`. It exports the API base, issuer and audience. It reads each variable once, with the same defaults.
2. Add `bearerHeader(token: string)` to `e2e/support/frontdoor_api.ts`. It returns the `Authorization` header object.
3. Replace the copies in the two files with imports from these modules.
4. Do not change any default value.

## Frontdoor Blackbox Test Plan
- The identity negative scenarios (TASK-0535, complete) pass unchanged. They prove that the behaviour is the same.
- Run the e2e suite once with the default environment and once with `PLAYWRIGHT_BASE_URL` set.

## Definition of Done
- One source for each default value under `e2e/support`.
- One `bearerHeader` builder used by all e2e steps.
- E2E suite passes. `make lint` passes. No file over 500 lines.
- No backward-compatibility shim (DoR 9).

## Audit Provenance
- Severity: low
- Source audits: `frontend-ui`
