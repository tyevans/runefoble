---
id: '0718'
title: Services Initialize Telemetry and the How-To Matches the Code
status: Refined
created: 2026-11-17
dependencies: []
governing_adrs:
- ADR-0015
governing_prds: []
governing_stories: []
target_bc: core
target_release: 0.9.0
---
# TASK-0718: Services Initialize Telemetry and the How-To Matches the Code

## Status
Refined. Found by the refactor audit round r1 and checked against the code by the orchestrator.

## Summary
Only the gateway calls `init_telemetry`. The how-to guide tells services to call it. Services emit no spans. `telemetry.py` also mixes four jobs.

## Problem Statement
- `init_telemetry` has one caller: `gateway/api/src/gateway_api/main.py:114`. No service imports `runefoble_platform.telemetry` or `opentelemetry`.
- `docs/how-to/instrument-services-with-opentelemetry.md:24-32` shows `init_telemetry("the-watcher", app=app)` as the service pattern.
- `libs/runefoble_platform/src/runefoble_platform/telemetry.py` (238 lines): setup (`init_telemetry`, line 39, 68 lines), FastAPI instrumentation (109, 121), Redis trace propagation (134, 170), span helper (217).

## Documentation & Architecture Review
- AGENTS.md hard invariants and DoR 9 (no compatibility shims).
- ADR-0015.
- `docs/how-to/` and `docs/reference/` pages named in the specification.

## Product & User Story References
None. Platform quality work.

## Detailed Specification & Implementation Plan
1. Check first whether the exporter blocks start-up when the collector is down. Fix if it does.
2. Split `telemetry.py` into a `telemetry/` package: `setup.py`, `propagation.py` (used by `redis_bus.py` and `event_deserializer.py`), `spans.py`. Update imports. No re-export shim.
3. Add `init_service_telemetry(name, settings, app)` and call it in each FastAPI service lifespan.
4. Correct the how-to to match the code. Add a reference entry for the settings.

## Frontdoor Blackbox Test Plan
- With `RUNEFOBLE_OTEL_ENABLED=true` and an in-process span exporter, one request to a public route of a service yields a server span with the service name.
- A Redis publish through the event bus carries a trace field.
- With the collector unreachable, the service still starts.

## Definition of Done
- The specification steps are done and the tests above pass.
- Docs named in the specification are corrected.
- `uv run pytest`, `make lint` and `make health-check` pass. No file over 500 lines.

## Audit Provenance
- Severity: medium
- Source audits: `refactor-r1/libs.md`
