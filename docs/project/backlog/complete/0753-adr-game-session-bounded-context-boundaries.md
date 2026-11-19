---
id: '0753'
title: 'ADR Spike: Decide Bounded Context Boundaries Inside game_session'
status: Complete
created: 2026-11-17
dependencies: []
governing_adrs:
- ADR-0007
- ADR-0015
governing_prds: []
governing_stories: []
target_bc: game_session
target_release: 0.9.0
---
# TASK-0753: ADR Spike: Decide Bounded Context Boundaries Inside game_session

## Status
Complete

## Summary
`game_session` holds about nine domains. `docs/reference/architecture-overview.md:42` lists only sessions, turns, dice, and spectator view. This spike decides the boundaries. It does not move code.

## Problem Statement
- Domains found under `services/game_session/src/game_session/`: campaign lifecycle and invites (`campaign/`), session and combat (`aggregate/`, `models/`, `reactions/`, `routers/combat.py`), tavern, minigames, and merchants (`minigames.py`, `minigame_tables/`, `merchants.py`), settlement, haggling, workers, and bulletin (`settlement/`, `settlements/`), caravans and contracts (`caravan/`, `contracts/`), West Marches and stronghold (`west_marches.py`, `stronghold.py`), child index and bounties (`child_index.py`).
- The audit proposes four packages: `campaign`, `play`, `settlement`, and `world`. It also asks whether `settlement` becomes its own service. No open task decides this.

## Documentation & Architecture Review
- AGENTS.md hard invariants and DoR 9 (no compatibility shims).
- ADR-0007, ADR-0015.
- ADR-0007 (DDD), ADR-0015 (a), ADR-0017 (file length), `docs/reference/architecture-overview.md`, TASK-0491 and TASK-0550 (related, narrower).

## Product & User Story References
None. Platform quality work.

## Detailed Specification & Implementation Plan
1. Write the ADR (ADR-0021, because ADR-0020 was taken) as `docs/project/adrs/accepted/adr-0021-game-session-internal-bounded-contexts.md`. The user accepted it on 2026-11-19. Decide: the package list, the owner of each current module, whether any package becomes a deployable service, the import rule between packages (ports only), and the migration order.
2. Keep the OpenAPI paths and WebSocket routes unchanged in the first step.
3. Update the `game_session` row in `docs/reference/architecture-overview.md` and in AGENTS.md if the ADR changes the layout.
4. Follow-up tasks (file them in the PR, at most two): TASK-0754 (client ports) and TASK-0755 (service container). This spike files no migration plan.

## Frontdoor Blackbox Test Plan
- No code change. The spike is done when the ADR is accepted and `spec-ops health` passes.

## Definition of Done
- ADR is accepted and listed in `docs/project/adrs/REGISTRY.md`. Architecture overview matches it.
- `uv run pytest`, `make lint`, and `make health-check` pass. No file over 500 lines.
- Docs touched by the change are correct. `CHANGELOG.md` has an `[Unreleased]` entry.

## Audit Provenance
- Severity: medium
- Source audits: `game-session.md (F4)`
