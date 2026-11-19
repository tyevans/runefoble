---
id: '0873'
title: Campaign Analytics Startup Is Configured Through Settings, Not Patched Module Globals
status: Refined
created: 2026-11-18
dependencies: []
governing_adrs:
- ADR-0007
- ADR-0014
governing_prds:
- PRD-0012
governing_stories:
- US-0040
target_bc: campaign_analytics
target_release: 0.9.0
---
# TASK-0873: Campaign Analytics Startup Is Configured Through Settings, Not Patched Module Globals

## Status
Refined.

## Summary
The campaign analytics startup tests patch two module attributes of `services/campaign_analytics` (`platform_settings` and `event_bus_provider`). The module builds both at import time. The tests therefore do not run the public startup path. Build the app through a factory that takes explicit settings. The tests then call the factory with environment settings.

## Problem Statement
- `tests/test_blackbox_campaign_analytics_startup.py:36`, `:54`, `:73-74`: `monkeypatch.setattr(analytics_main, "platform_settings", ...)` and `monkeypatch.setattr(analytics_main, "event_bus_provider", EventBusProvider(settings))`.
- The module attributes are created when `analytics_main` is imported. A test that patches them does not exercise the environment-driven startup that a deployment uses.
- AGENTS.md Hard Invariant 7 forbids private internals in blackbox tests.

## Documentation & Architecture Review
- ADR-0007 (bounded context owns its composition root). ADR-0014 (blackbox tests use public entry points).
- `docs/how-to/instrument-services-with-opentelemetry.md` and `docs/reference/platform-services.md` describe the startup environment. Check both.

## Product & User Story References
- PRD-0012 (campaign telemetry and chronicle). US-0040 (combat telemetry and living timeline).

## Detailed Specification & Implementation Plan
1. In `services/campaign_analytics`, add `create_app(settings, event_bus)` in the composition root. The module-level `app` uses `create_app` with settings read from the environment.
2. The store check still raises `CampaignStoreStartupError` and `StorageConfigurationError` at startup. Raise them from `create_app`.
3. Update the startup tests to set environment variables, or call `create_app` with explicit settings. Do not patch module attributes.
4. Remove the module-level patch targets. The module must not expose them as mutable globals used by tests.

## Frontdoor Blackbox Test Plan
- Startup with a missing store configuration fails with `StorageConfigurationError`. Assert the same error name and message.
- Startup with an unreachable store fails with `CampaignStoreStartupError`.
- Startup with valid environment settings serves `GET /openapi.json` through `TestClient`.

## Definition of Done
- No `monkeypatch.setattr` on `analytics_main` in `tests/`.
- Startup tests pass with the same named errors.
- `uv run pytest` and `make health-check` pass. No file over 500 lines.
- No backward-compatibility shim (DoR 9).

## Audit Provenance
- Severity: medium
- Source audits: `tests`
