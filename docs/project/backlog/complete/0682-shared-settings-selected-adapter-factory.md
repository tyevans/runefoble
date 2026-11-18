---
id: '0682'
title: Shared Settings-Selected Adapter Factory for Engine Ports
status: Complete
created: 2026-11-17
dependencies: []
governing_adrs:
- ADR-0003
- ADR-0015
governing_prds: []
governing_stories: []
target_release: 0.9.0
---

# TASK-0682: Shared Settings-Selected Adapter Factory for Engine Ports

## Status
Complete

## Summary
Five tasks added the same pattern: an engine port, a settings field that selects the adapter, a test-only fake injected at the composition root, start-up validation and an honest 503 when the engine fails. Each service wrote its own version. This task extracts the shared part into `libs/` and moves the services onto it.

## Problem Statement
- Voice STT (TASK-0600) and TTS (TASK-0601) in `services/voice_agent`, map generator (TASK-0614) and wardrobe generator (TASK-0615) in `services/asset_forge`, and embeddings (TASK-0616, `libs/runefoble_embeddings`) each define their own selector, registry and error-to-503 mapping.
- Duplicated logic belongs in a lib (AGENTS.md audit brief, DDD and SOLID rules).

## Documentation & Architecture Review
- ADR-0015: deployed services fail fast when a configured backend is unreachable. No fallback to fakes.
- Write `docs/how-to/add-an-engine-port-adapter.md` (Diataxis how-to) for the shared pattern.

## Product & User Story References
None. Internal refactor with no change to public behaviour.

## Detailed Specification & Implementation Plan
1. Read the five implementations. Extract only the common parts into `libs/runefoble_platform` (or a new small lib if it does not fit): an adapter registry keyed by setting value, a `build_adapter(settings_value)` that raises a clear start-up error for unknown values, and one `EngineUnavailableError` with a FastAPI exception handler that returns 503 with an error code.
2. Move each service to the shared parts. Keep domain-specific port interfaces in the owning service.
3. Delete the per-service copies. No aliases or re-exports.
4. Write the how-to page.

## Frontdoor Blackbox Test Plan
- Existing frontdoor tests for STT, TTS, map, wardrobe and embedding failure paths still pass unchanged (they assert 503 codes and payloads).
- New lib test: an unknown setting value fails at app start-up with a message that names the allowed values.

## Definition of Done
- One shared factory and error handler. No duplicate selector code in the services.
- All touched services' tests pass. How-to written. CHANGELOG line given to the orchestrator.

## Audit Provenance

- Severity: medium
- Source audits: `work/0600.md`, `work/0601.md`, `work/0614.md`, `work/0615.md`, `work/0616.md`
