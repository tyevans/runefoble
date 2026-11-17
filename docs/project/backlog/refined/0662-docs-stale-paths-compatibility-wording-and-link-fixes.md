---
id: '0662'
title: Reference and How-To Docs Drop Stale Paths, Compatibility Wording, and Machine-Specific Links
status: Refined
created: 2026-11-17
dependencies: []
governing_adrs:
- ADR-0007
- ADR-0003
governing_prds: []
governing_stories: []
target_release: 0.9.0
severity: medium
source_audits:
- w3-docs-integrity.md
---

# TASK-0662: Reference and How-To Docs Drop Stale Paths, Compatibility Wording, and Machine-Specific Links

## Status
Refined

## Summary
Several reference and how-to pages cite module paths that do not exist, describe backward-compatibility layers (forbidden by DoR 9), state line counts that are wrong, and link to absolute paths on one developer's machine. Correct each one to the real path, delete the compatibility wording, and make the links repository-relative. Where the code still has the shim, the wording names it as a defect and points to the shim-removal task instead of calling it intended behaviour.

## Problem Statement
- R1 (medium, `docs/reference/redis-streams-event-bus.md`): line 32 `libs/runefoble_platform/redis_bus.py` (actual `libs/runefoble_platform/src/runefoble_platform/redis_bus.py`). Line 36 `libs/runefoble_platform/consumer_group.py` (actual path has `src/runefoble_platform/`). Line 44 `services/game_session/projections/` (actual `services/game_session/src/game_session/projections/`). Line 50 calls the projections "Re-exported ... for backward compatibility".
- R3 (low): the diagram (line 14) says `events.session`. Line 59 says `runefoble.events.session`. Use one name.
- PS1 (medium, `docs/reference/platform-services.md`): line 42 and the table present the `InMemoryEventStore`, `InMemoryEventBus`, and "In-Memory Object Store Mock" fallbacks as design. Name them as test-only or state that production falls back on error.
- PS2 (medium): the Zitadel section does not state that `RUNEFOBLE_AUTH_DEV_MODE` defaults to `True` (`libs/runefoble_platform/src/runefoble_platform/config.py:69-72`). State the default and require `false` outside local development.
- PS3 (low): the SpiceDB sync path accepts `MockSpiceDBClient` (`libs/runefoble_auth/src/runefoble_auth/sync.py:9,38,141`). Note the exception.
- M1 (medium, `docs/reference/fastmcp-gateway.md`): line 11 calls `dynamic_registry.py` "Backward-compatible re-exports". The tool inventory implies the static tools work. Mark the canned tools as not implemented.
- H1 (low, `docs/how-to/run-autonomous-backlog-engine.md:105-113`): nine `file:///home/ty/...` absolute links. Use repository-relative links.
- H2 (low, `docs/how-to/simulate-npc-faction-agendas-and-world-ticks.md:31`): `services/the_watcher/src/the_watcher/factions.py` (actual `services/the_watcher/src/the_watcher/factions/factions.py`).
- X2 (low, `docs/explanation/the-watcher-autonomous-dm.md:38`): `movement_parser.py` is 192 lines, not "under 180". Lines 32 and 38 say "backward-compatible". Correct both.
- X1 (medium, `docs/explanation/the-watcher-autonomous-dm.md:24`): auto-pilot is described as persisting actions and emitting events end to end. The save and publish code exists (`services/game_session/src/game_session/routers/autopilot.py:122,138`), but activation does not work (TASK-0658 and the character-sheet stand-in work). Qualify the claim with the blocker.
- X3 (low, `docs/explanation/realtime-voice-and-board-sync.md:85,98,107,113`): "legacy imports", "seamless compatibility", "backward-compatible alias", and re-exports. Remove the wording. TASK-0487 removes the code.

## Documentation & Architecture Review
- Diataxis: reference pages state what exists. Explanation pages state the design and its current status. Each fix keeps the page in its quadrant.
- DoR 9: no compatibility wording in any spec. Where a shim still exists, the page names the removal task (TASK-0485 to TASK-0502, TASK-0487 for events).
- The paths are verified with a script before editing, so the correction is not another guess.

## Product & User Story References
Documentation accuracy. Not user-facing.

## Detailed Specification & Implementation Plan
1. Build a script (`scripts/check_doc_paths.py`, run with `uv run`) that extracts backticked repository paths from `docs/reference`, `docs/how-to`, and `docs/explanation`, and reports each one that does not exist.
2. Correct every path the script reports, using the real file.
3. Replace each `file:///home/ty` link with a relative link.
4. Qualify the auto-pilot claim (X1). Remove the compatibility wording listed above. Add a link to the removal task where the code still exists.
5. Correct the line counts and names listed above. Re-count with `wc -l` at the time of the edit.
6. Do not change `docs/tutorials/` (TASK-0657 and TASK-0658 own them) or `docs/marketing.md` (TASK-0659).

## Frontdoor Blackbox Test Plan
- `scripts/check_doc_paths.py` reports zero missing paths across the three quadrants and fails when a file has `file:///` or a backward-compatibility phrase outside a link to a removal task. Before the edit it reports the paths above. After the edit it reports none.
- A markdown link check passes for the same directories.
- A grep for "backward" and "legacy" in the three quadrants returns only lines that name a removal task.

## Definition of Done
1. `scripts/check_doc_paths.py` passes for the three quadrants.
2. Every item listed above is corrected in the file it names.
3. No compatibility wording remains outside a removal-task reference.
4. Absolute `file:///` links are gone from `docs/how-to`.
5. The check runs in `make health-check` or in `spec-ops health` (decision in TASK-0668).
6. Files stay under 500 lines.
