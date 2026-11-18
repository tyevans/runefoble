---
id: '0692'
title: Node Service Dev Script Resolves Its Imports and the Image Pins pnpm
status: Refined
created: 2026-11-17
dependencies:
- TASK-0621
governing_adrs:
- ADR-0010
governing_prds: []
governing_stories: []
target_release: 0.9.0
severity: low
source_audits:
- work/0621.md
- work/0575.md
---

# TASK-0692: Node Service Dev Script Resolves Its Imports and the Image Pins pnpm

## Status
Refined. Discovered in round 2 audit of reports 0621 and 0575.

## Summary
The audience studio `dev` script runs TypeScript with a flag that cannot resolve the `.js` import paths. The root package has no `packageManager` field, so the image build installs whatever pnpm major `corepack` picks up.

## Problem Statement
- `services/audience_studio/package.json:10`: `"dev": "node --experimental-strip-types src/index.ts"`. The `.js` imports do not resolve. This is audit F7.
- Root `package.json` has no `packageManager` field. `deployments/docker` relies on `corepack enable`, which picks the newest pnpm. Report 0621 saw pnpm 12.x while the lock file is for an older major.

## Documentation & Architecture Review
- ADR-0010: CI and build reproduce from the lock file.
- `docs/reference/cli-interfaces.md`: state the dev command for audience studio.

## Product & User Story References
None. Developer tooling.

## Detailed Specification & Implementation Plan
1. Change the dev script to a runner that resolves `.js` to `.ts` (for example `tsx watch`), add the dev dependency, and keep the same entry file.
2. Add `"packageManager": "pnpm@<version from the lock file>"` to the root `package.json`. Use the same version in the Dockerfile `corepack` step.
3. Run the audience studio dev server once in the Makefile target and confirm it serves.

## Frontdoor Blackbox Test Plan
- Start the audience studio dev server. `GET /health` (public route) returns 200.
- The Docker image build installs with the pinned pnpm. The lock file is unchanged by the build.

## Definition of Done
- Dev script starts. Root `packageManager` set. Image build pins pnpm.
- `pnpm run build` and `make images` pass for audience studio.
