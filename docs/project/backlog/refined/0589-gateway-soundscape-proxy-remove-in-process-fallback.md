---
id: '0589'
title: Gateway Soundscape Proxy Removes In-Process Fallback and Service Imports
status: Refined
created: 2026-11-17
dependencies:
- TASK-0436
- TASK-0580
governing_adrs:
- ADR-0006
- ADR-0007
governing_prds:
- PRD-0010
governing_stories:
- US-0039
- US-0053
target_release: 0.9.0
---

# TASK-0589: Gateway Soundscape Proxy Removes In-Process Fallback and Service Imports

## Status
Refined

## Summary
TASK-0436 added the gateway soundscape proxy. The shipped router still runs the `soundscape` package in process when the proxy fails, and it still imports soundscape internals. This task removes both. The gateway forwards to the soundscape service only, through the shared client. The default port is fixed in Helm (TASK-0624), not in code.

## Problem Statement
- `gateway/api/src/gateway_api/routers/soundscape.py:21` defaults to `http://soundscape:8010`. Port 8010 is audience-studio. The soundscape service listens on 8009 (`w2-soundscape.md` F8, `w1-gates-infra.md` F1).
- `SOUNDSCAPE_SERVICE_URL` is not set in Helm. Every call falls back to the in-process import (`w2-soundscape.md` F8).
- `soundscape.py:9-14` imports `soundscape.models`, `soundscape.routers.cue`, `leitmotif`, `stems` and `tension`. It calls their functions with `spicedb=get_spicedb_client()` (`w2-soundscape.md` F16, `w1-gateway-api.md` F10).
- `soundscape.py:24-37` (`_proxy_or_fallback`) uses `except Exception: pass` (`w1-gateway-api.md` F13).
- The gateway therefore runs its own soundscape state. That state is separate from the microservice's state.

## Documentation & Architecture Review
- This task is a follow-up to TASK-0436. TASK-0436 is treated as implemented. Its spec still says "in-process fallback" (`0436` Detailed Specification step 1). This task removes that part.
- The soundscape service owns the tension, stem and cue state (`services/soundscape/src/soundscape/routers/`). Its routers use prefix `/api/v1/soundscape` and `/api/v1/soundscape/leitmotif`.
- The gateway also declares `POST /override` as an alias of `POST /stems/override`, and `GET /leitmotif/profile/{id}` as an alias of `GET /leitmotif/{id}`. DoR 9 forbids aliases. Remove them. Check the owner for each path first.
- Authorization on the soundscape mutations is owned by the authorization theme (`w2-soundscape.md` F7). This task forwards the caller identity only.

## Product & User Story References
- [`prd-0010-adaptive-soundscape-foley-and-tension-scoring.md`](../../product/accepted/prd-0010-adaptive-soundscape-foley-and-tension-scoring.md)
- [`us-0039-encounter-tension-adaptive-scoring-and-foley.md`](../../user_stories/accepted/us-0039-encounter-tension-adaptive-scoring-and-foley.md)
- [`us-0053-dm-manual-soundboard-and-foley-triggers.md`](../../user_stories/accepted/us-0053-dm-manual-soundboard-and-foley-triggers.md)

## Detailed Specification & Implementation Plan
1. Rewrite `routers/soundscape.py` as pure proxies through `ServiceClient` (TASK-0580). Routes: `POST /api/v1/soundscape/cue`, `GET /api/v1/soundscape/tension`, `POST /api/v1/soundscape/tension/calculate`, `POST /api/v1/soundscape/stems/override`, `GET /api/v1/soundscape/leitmotif/{character_id}`. Each handler is 10 lines or fewer.
2. Delete `_proxy_or_fallback`, the soundscape package imports and the `get_spicedb_client` call in this file.
3. Remove the `SOUNDSCAPE_SERVICE_URL` code default. The value comes from the settings field in TASK-0580 and the Helm variable in TASK-0624.
4. Remove the alias routes `POST /override` and `GET /leitmotif/profile/{id}`. Update the frontend call sites in the same change (search `frontend/` and `services/soundscape/ui/`).
5. Correct the port text in TASK-0436 and TASK-0498 in the index, not by editing those files (see the index report).

## Frontdoor Blackbox Test Plan
Test file: `tests/test_blackbox_soundscape_gateway.py` (existing file, updated). The soundscape service runs as an ASGI app.

| Case | Expected before fix | Expected after fix |
|---|---|---|
| `POST /api/v1/soundscape/cue` returns the service's cue id | Fails: passes only via in-process import | Passes |
| Service down returns 503, not the in-process result | Fails: 200 from in-process fallback | Passes |
| `POST /api/v1/soundscape/override` returns 404 | Fails: 200 alias | Passes |
| `rg "from soundscape" gateway/api/src` | Fails: matches | Passes: no match |

## Definition of Done
1. `routers/soundscape.py` has no import from `soundscape` and no fallback.
2. The alias routes are removed. Frontend callers are updated.
3. The blackbox test file passes. `uv run ruff check .` passes.
4. `docs/reference/ports-and-endpoints.md` shows soundscape on port 8009 and the gateway routes.

## Audit Provenance

- Severity: high
- Source audits: `w2-soundscape.md`, `w1-gateway-api.md`, `w1-gates-infra.md`
