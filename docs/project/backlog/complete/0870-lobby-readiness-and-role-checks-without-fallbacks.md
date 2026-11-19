---
id: '0870'
title: Lobby Readiness Has No Role Fallback and Role Checks Use One Normalizer
status: Complete
created: 2026-11-18
dependencies: []
governing_adrs:
- ADR-0001
- ADR-0013
- ADR-0015
governing_prds:
- PRD-0023
governing_stories:
- US-0063
- US-0065
target_bc: game_session
target_release: 0.9.0
---
# TASK-0870: Lobby Readiness Has No Role Fallback and Role Checks Use One Normalizer

## Status
Complete

## Summary
When a session has no player, the lobby counts every non-spectator as a player. A DM-only session then shows DMs as ready players. Role strings also drive owner and manage controls in several files. Remove the fallback. Route role checks through one normalizer and through permission flags from the server.

## Problem Statement
- `services/game_session/ui/src/lobby/types.ts:73-78`: the player filter excludes four role names (`spectator`, `dm`, `dungeon_master`, `owner`). The fallback at line 76-78 re-evaluates all non-spectators as players when the player list is empty. A DM-only session then counts the DM as a player.
- `services/game_session/ui/src/campaigns/runefoble-campaign-members.ts:130` compares `member.role === 'owner'`. Lines 148-150 map `'dm'` and `'dungeon_master'` to options.
- The string `'dm'` appears in 11 lines of `frontend/src` and `services/*/ui/src`. The audit report counted 108 occurrences. The recount is lower.
- `frontend/src/services/campaign-capabilities.ts` holds the capability flags for the shell. A service UI package cannot import shell code (ADR-0013). The flags must reach the service element as properties from the server.

## Documentation & Architecture Review
- ADR-0001 (SpiceDB decides object permissions). The UI must not decide by role name (Hard Invariant 1).
- ADR-0013 (service UI packages do not import the shell).
- `docs/how-to/coordinate-game-session-lobby-and-readiness.md` describes readiness. Update it.

## Product & User Story References
- PRD-0023. US-0063 (campaign roles). US-0065 (lobby readiness and launch).

## Detailed Specification & Implementation Plan
1. Delete the fallback in `computeReadinessSummary` (`lobby/types.ts:76-78`). With no player, the summary shows zero players.
2. Add `services/game_session/ui/src/lobby/roles.ts` with one `normalizeRole()` and one list of coordinator roles. Use it in `types.ts` and `runefoble-campaign-members.ts`.
3. Replace the `'owner'` and manage checks in `runefoble-campaign-members.ts` with a permission flag property. The shell passes the flag from the server response.
4. In the lobby readiness view, show "No players have joined" when the player count is zero.
5. Update the Storybook stories for the lobby and members views.

## Frontdoor Blackbox Test Plan
- Playwright BDD (ADR-0014): a session that holds only a DM shows zero players in the readiness text.
- Playwright BDD: a member without the manage permission does not see the role select.
- Playwright BDD: a player who is ready raises the ready count. This is the existing behaviour and must not change.

## Definition of Done
- No role-name comparison outside `roles.ts` in the game session UI.
- No readiness fallback in `lobby/types.ts`.
- Playwright BDD scenarios pass without backdoor state changes.
- Storybook stories have zero console errors.
- `pnpm run build` and `make lint` pass. No file over 500 lines.
- No backward-compatibility shim (DoR 9).

## Audit Provenance
- Severity: medium
- Source audits: `frontend-ui`

## Completion Note
The Playwright scenarios moved to TASK-0840 (addendum 3 and 4).
