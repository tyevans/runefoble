---
id: '0620'
title: Shared Python Service Dockerfile and make images Kind Load Target
status: Refined
created: 2026-11-17
dependencies: []
governing_adrs:
- ADR-0003
- ADR-0005
governing_prds: []
governing_stories:
- US-0010
target_release: 0.9.0
severity: high
source_audits:
- w1-gates-infra.md
- w2-soundscape.md
- w2-inference-worker.md
- w1-gateway-mcp.md
---

# TASK-0620: Shared Python Service Dockerfile and make images Kind Load Target

## Status
Refined

## Summary
Every Helm Deployment references `runefoble/<service>:0.1.0`, but only `frontend/Dockerfile` exists in the repository. Add one shared, parameterized Dockerfile for the Python uv-workspace services and a `make images` target that builds every Python image and loads it into the `runefoble-local` Kind cluster. After `make cluster-up && make images && make helm-deploy`, every Python Deployment must reach Ready.

## Problem Statement
- `find . -iname '*dockerfile*'` returns only `./frontend/Dockerfile` (`.audit/reports/w1-gates-infra.md` F3).
- `deployments/helm/runefoble/values.yaml` lists `image: runefoble/<name>:0.1.0` for gateway-api, the-watcher, board-state, character-sheet, game-session, voice-agent, campaign-lore, rules-compendium, asset-forge, soundscape and campaign-analytics.
- `Makefile` has no `docker build` or `kind load` target. `helm-deploy` (Makefile, `helm-deploy` target) leaves every pod in ImagePullBackOff.
- `services/soundscape` Helm container has no `command` (`deployments/helm/runefoble/templates/soundscape.yaml`); the image cannot be built from this repository (`w2-soundscape.md` F14).

## Documentation & Architecture Review
- `docs/reference/cli-interfaces.md`: Makefile target reference. Add `make images` on completion.
- `docs/how-to/create-a-new-service-bc.md`: service scaffold must add a row to the image table.
- ADR-0003 (uv workspace): images must install through `uv sync --frozen --package <name>`, never pip.
- ADR-0005 (Kind + Helm): images are loaded into Kind, not pushed to a registry.

## Product & User Story References
- US-0010 (developer local infrastructure, `docs/project/user_stories/accepted/us-0010-*.md`).

## Detailed Specification & Implementation Plan
1. Add `deployments/docker/python-service.Dockerfile` (single file, no per-service copy):
   - Base `python:3.13-slim`. Install `uv` from the official image.
   - `COPY` the workspace (`pyproject.toml`, `uv.lock`, `libs/`, `services/`, `gateway/`).
   - Build args: `SERVICE` (uv member name, e.g. `game-session`), `APP` (ASGI path, e.g. `game_session.main:app`), `PORT`.
   - Run `uv sync --frozen --package $SERVICE --no-dev`, then `CMD` runs `uvicorn $APP --host 0.0.0.0 --port $PORT` through the venv.
   - Expose `$PORT`. No dev dependencies, no tests copied.
2. Add a `make images` target and a `IMAGE_TABLE` variable in the Makefile listing `image-tag | SERVICE | APP | PORT` for: gateway-api (8000), the-watcher (8001), board-state (8002), character-sheet (8003), game-session (8004), voice-agent (8005), campaign-lore (8006), rules-compendium (8007), asset-forge (8008), soundscape (8009), campaign-analytics (8011). Ports must equal `deployments/helm/runefoble/values.yaml` `services.*.port`.
3. `make images` runs `docker build` per row with `-t runefoble/<name>:0.1.0`, then `kind load docker-image --name $(CLUSTER_NAME)` for each tag.
4. Add `services/soundscape` container `command` only if the image does not set one. Prefer the image CMD and leave Helm `command` empty.
5. Add `.dockerignore` at repo root excluding `.git`, `.venv`, `node_modules`, `.audit`, `docs`, `e2e`, `frontend`.
6. `make helm-deploy` depends on `images` only when `IMAGES=1` is not set to skip. Keep the default explicit: document `make cluster-up images helm-deploy` in `docs/tutorials/01-local-development-setup.md`.

Out of scope: audience-studio (TypeScript, TASK-0621), inference-worker (TASK-0622), gateway-mcp (TASK-0623).

## Frontdoor Blackbox Test Plan
- Before fix: `make images` fails (no target). `docker run -p 18000:8000 runefoble/gateway-api:0.1.0` is not possible.
- After fix: `make images` exits 0. For each built image, `docker run -d -p <host>:<PORT> runefoble/<name>:0.1.0` then `GET http://localhost:<host>/openapi.json` returns HTTP 200 with a `paths` object. A pytest module (`tests/test_blackbox_deployability_images.py`, marked `docker`) performs these calls through HTTP only.
- Helm check: the image tags in `helm template` output equal the tags built by `make images`.

## Definition of Done
1. `deployments/docker/python-service.Dockerfile`, `.dockerignore`, and `make images` exist and pass.
2. Each Python service image serves `/openapi.json` on its Helm port.
3. `make cluster-up images helm-deploy` on a clean Kind cluster reaches Ready for all Python Deployments (manual gate, recorded in the PR).
4. `docs/reference/cli-interfaces.md` and the tutorial list the new target.
5. `make lint` and `uv run ruff check .` pass. No source file above 500 lines.
