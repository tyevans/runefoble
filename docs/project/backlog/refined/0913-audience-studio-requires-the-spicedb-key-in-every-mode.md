---
id: '0913'
title: Audience Studio Requires the SpiceDB Key in Every Mode
status: Refined
created: 2026-11-19
dependencies: []
governing_adrs:
- ADR-0015
- ADR-0001
governing_prds: []
governing_stories: []
target_bc: audience_studio
target_release: 0.9.0
---
# TASK-0913: Audience Studio Requires the SpiceDB Key in Every Mode

## Status
Refined

## Summary
`readSpicedbPresharedKey` returns an empty key when `NODE_ENV` is `test`. The file header says that neither value has a default. An environment variable must not turn off a fail-fast check. The entrypoint also reads all settings at module load, outside `main`.

## Problem Statement
- `services/audience_studio/src/config.ts:30-41`: the `NODE_ENV === 'test'` branch returns `''`.
- `services/audience_studio/src/config.ts:1-5`: the header says "Neither value has a default."
- `services/audience_studio/src/index.ts:12-15`: endpoint, key, Zitadel and store settings are read at module load.
- The store settings already refuse the memory backend "also when NODE_ENV is test" (`services/audience_studio/test/config.test.ts:73-89`). The key check is the only exception.

## Documentation & Architecture Review
- ADR-0015 decisions (c) and (f), problem 4. TASK-0625 (complete) removed hardcoded key defaults.
- `docs/reference/audience-studio-api.md` and `docs/reference/platform-services.md`: check the stated environment rules.
- DoR 9: no test-mode exception.

## Product & User Story References
None. Platform quality work.

## Detailed Specification & Implementation Plan
1. Delete the `NODE_ENV` branch from `readSpicedbPresharedKey`. Update the doc comment.
2. Move the four settings reads in `index.ts` into `main()`, so that import of the module has no side effect and a missing value fails at start with one error.
3. Tests that build the server pass a key in their env or through `buildServer` options (the fake SpiceDB client in `test/fakeSpiceDb.ts` does not need a real key).

## Frontdoor Blackbox Test Plan
- `services/audience_studio/test/config.test.ts`: "a missing key throws" for `NODE_ENV` unset, `production` and `test`.
- `services/audience_studio/test/dev_script.test.ts`: starting the entrypoint without the key exits non-zero with the key name in the message.
- All other audience studio tests pass.

## Definition of Done
- No `NODE_ENV` check in `config.ts`.
- `pnpm` test and build for audience studio, `make build` and `make health-check` pass. No file over 500 lines.

## Audit Provenance
- Severity: medium
- Source audits: `gateways-libs.md` (F2, and the audience studio part of F4)
