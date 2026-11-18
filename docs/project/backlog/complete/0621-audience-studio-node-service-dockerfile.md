---
id: '0621'
title: Audience Studio Node Service Dockerfile and Image Build
status: Complete
created: 2026-11-17
dependencies:
- TASK-0620
governing_adrs:
- ADR-0004
- ADR-0005
governing_prds:
- PRD-0011
governing_stories: []
target_release: 0.9.0
---

# TASK-0621: Audience Studio Node Service Dockerfile and Image Build

## Status
Complete

## Summary
`services/audience_studio` is a TypeScript HTTP service deployed by Helm (`deployments/helm/runefoble/templates/audience-studio.yaml`, image `runefoble/audience-studio:0.1.0`). It has no Dockerfile and is not in `make images`. Add a Node Dockerfile and include the image in the `make images` target from TASK-0620.

## Problem Statement
- The audience-studio image cannot be built from this repository (`.audit/reports/w1-gates-infra.md` F3, Python and TypeScript both missing).
- The package `dev` script does not start (`w2-audience-studio.md` F7); the production entry must be the compiled `dist/index.js`, so the image must run the build.
- `services/audience_studio` is excluded from the uv workspace and listed in `pnpm-workspace.yaml`. The Dockerfile must install with pnpm from the lockfile.

## Documentation & Architecture Review
- ADR-0004 (Lit and Storybook): the audience UI package is built separately; the image needs only the server package.
- ADR-0005: image loaded into Kind through TASK-0620's target.
- `docs/reference/ports-and-endpoints.md` lists audience-studio on 8010; keep it.

## Product & User Story References
- PRD-0011 (live spectator studio and audience interactivity), `docs/project/product/accepted/prd-0011-live-spectator-studio-and-audience-interactivity.md`.

## Detailed Specification & Implementation Plan
1. Add `services/audience_studio/Dockerfile` (multi-stage): stage 1 `node:20-alpine` (match `frontend/Dockerfile`), `corepack enable`, copy root `package.json`, `pnpm-lock.yaml`, `pnpm-workspace.yaml`, and `services/audience_studio/package.json`, run `pnpm --filter @runefoble/audience-studio install --frozen-lockfile`, copy sources, run its build script. Stage 2 `node:20-alpine` runs as a non-root user, copies `dist/` and production `node_modules`, sets `PORT=8010`, `HOST=0.0.0.0`, `CMD ["node", "dist/index.js"]`.
2. Add `audience-studio` to the `make images` target (TASK-0620), with context set to the repository root and `-f services/audience_studio/Dockerfile`.
3. Confirm `GET /healthz`, `GET /readyz`, `GET /openapi.json` on the built image.
4. Do not change application logic in this task.

## Frontdoor Blackbox Test Plan
- Before fix: `docker build -f services/audience_studio/Dockerfile .` fails (no file).
- After fix: build succeeds; `docker run -p 18010:8010 runefoble/audience-studio:0.1.0`; `GET /healthz` returns 200; `GET /openapi.json` returns 200. Test lives in `tests/test_blackbox_deployability_images.py` (shared with TASK-0620).

## Definition of Done
1. Dockerfile builds on a clean checkout with `--frozen-lockfile`.
2. Image starts as non-root and answers on 8010.
3. `make images` includes audience-studio.
4. `docs/reference/cli-interfaces.md` notes the image.
5. No file above 500 lines.

## Audit Provenance

- Severity: high
- Source audits: `w2-audience-studio.md`, `w1-gates-infra.md`
