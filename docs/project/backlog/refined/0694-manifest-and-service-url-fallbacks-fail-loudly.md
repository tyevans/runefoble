---
id: '0694'
title: UI Manifest and Service URL Fallbacks Fail Loudly
status: Refined
created: 2026-11-17
dependencies:
- TASK-0578
- TASK-0624
governing_adrs:
- ADR-0015
governing_prds: []
governing_stories: []
target_release: 0.9.0
---

# TASK-0694: UI Manifest and Service URL Fallbacks Fail Loudly

## Status
Refined. Discovered in round 2 audit of reports 0604, 0578 and 0624.

## Summary
Three start-up and read paths hide a broken setup. A broken manifest file falls back to a hardcoded manifest. The soundscape manifest does the same in a bare `except`. An unset Watcher URL makes autopilot skip The Watcher with no log. ADR-0015 says fallbacks hide failures. This task removes these fallbacks.

## Problem Statement
- `services/character_sheet/src/character_sheet/main.py:52-60`: an unreadable `ui/manifest.json` falls back to a hardcoded manifest. The `except Exception: pass` hides the cause.
- `services/soundscape/src/soundscape/main.py:88-93`: the same pattern in `get_ui_manifest`.
- `services/game_session/src/game_session/dependencies.py:31`: `WATCHER_SERVICE_URL` reads `RUNEFOBLE_WATCHER_URL` with no default. `routers/autopilot.py:74` skips The Watcher when it is unset, with no log entry.

## Documentation & Architecture Review
- ADR-0015 (4): fallbacks hide failures. A failed dependency must look failed.
- ADR-0013: the manifest is the contract for the App Shell. A missing or broken manifest is a build error.

## Product & User Story References
None. Startup and configuration hygiene.

## Detailed Specification & Implementation Plan
1. Manifest reads: a missing or invalid manifest raises at start-up. Remove the hardcoded manifest. Add the manifest to the build output check.
2. `WATCHER_SERVICE_URL` unset: game_session refuses to start in deployed mode. Tests set the URL to a test double.
3. Autopilot: a failed call to The Watcher returns an error or records a visible failure. It never silently runs the local engine instead of the configured one (align with TASK-0691).

## Frontdoor Blackbox Test Plan
- Start character sheet with the manifest removed. Start-up fails with a clear error.
- Start game session with `RUNEFOBLE_WATCHER_URL` unset. Start-up fails.
- Start game session with a Watcher test double that returns 503. The autopilot route returns 503 and no action is recorded.

## Definition of Done
- No hardcoded manifest and no silent Watcher skip in production code.
- `uv run pytest` and `make lint` pass.

## Audit Provenance

- Severity: medium
- Source audits: `work/0604.md`, `work/0578.md`, `work/0624.md`
