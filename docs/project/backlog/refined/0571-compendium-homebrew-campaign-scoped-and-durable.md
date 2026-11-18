---
id: '0571'
title: Compendium Homebrew Campaign-Scoped and Rebuilt From the Aggregate
status: Refined
created: 2026-11-17
dependencies:
- TASK-0560
- TASK-0561
governing_adrs:
- ADR-0011
- ADR-0007
governing_prds:
- PRD-0008
governing_stories:
- US-0052
- US-0034
target_release: 0.9.0
---

# TASK-0571: Compendium Homebrew Campaign-Scoped and Rebuilt From the Aggregate

## Status
Refined

## Summary
Homebrew monsters are written into the global SRD monster map with no campaign key. An anonymous request can read a campaign's homebrew "Goblin" in place of the SRD Goblin. Homebrew index state is also process memory, so it is lost on restart. This task keeps homebrew in campaign-scoped aggregate state, rebuilds the index from events, and prevents homebrew from replacing canonical entries.

## Problem Statement
- `services/rules_compendium/src/rules_compendium/retrieval.py`, `index_homebrew_rule`: `self._monsters[title.lower()] = m_data` writes into the global map (w2-rules-compendium F4).
- `GET /api/v1/compendium/monsters/{name}` returns homebrew for any caller. Probe: CR 99 "Goblin" replaced SRD Goblin CR 0.25.
- `routers/homebrew.py` `list_campaign_homebrew` reads `engine.get_homebrew_by_campaign()`, a process-memory dict (`self._homebrew`) (w2-rules-compendium F5).
- Authorization for the campaign-scoped read belongs to the security theme. This task only scopes the data.

## Documentation & Architecture Review
- `docs/how-to/balance-combat-encounters-and-query-compendium.md` describes homebrew registration. Verify it. Correct any claim that homebrew is global.
- The lore service has its own homebrew-like index. Not in scope.

## Product & User Story References
- [`us-0052-homebrew-spell-monster-and-rule-authoring.md`](../../user_stories/accepted/us-0052-homebrew-spell-monster-and-rule-authoring.md)
- [`us-0034-agnostic-ttrpg-ruleset-schemas-and-system-expansion.md`](../../user_stories/accepted/us-0034-agnostic-ttrpg-ruleset-schemas-and-system-expansion.md)

## Detailed Specification & Implementation Plan
1. `CompendiumAggregate` (keyed by campaign id) records `HomebrewMonsterRegistered` and `HomebrewRuleRegistered` events.
2. Keep canonical SRD data in a separate read-only source. Homebrew lookup is a second source keyed by campaign. A name collision with SRD returns the SRD entry, and the homebrew entry is listed as `shadowed`.
3. On start-up, rebuild the homebrew index from the stored events (or from a projection rebuilt from them). Delete `self._homebrew` as a source of truth.
4. Replace the broad `except Exception` in `homebrew.py` with `load_or_create` from TASK-0561.

## Frontdoor Blackbox Test Plan
- **Fail before, pass after:** register a homebrew monster for campaign A through the public route. Then `GET /api/v1/compendium/monsters/Goblin`. Before: CR 99. After: SRD Goblin CR 0.25.
- **Fail before, pass after:** restart the app, then list campaign A homebrew. Before: empty. After: the monster is listed.
- Public routes only.

## Definition of Done
1. Homebrew never writes to the SRD monster map (grep and test).
2. Restart and shadowing tests pass.
3. `uv run pytest` and `make health-check` pass. Files under 500 lines.
4. How-to and reference docs corrected. `CHANGELOG.md` entry.

## Orchestrator Addenda (2026-11-17, round 2)

Source: `.audit/synth/discovered-round2.md`.

- services/rules_compendium/src/rules_compendium/aggregate.py calls init_state() in lazy-init guards (lines 34, 143, 160, 177, 189). Use the eventsource initial-state hook and remove the guards.

## Audit Provenance

- Severity: high
- Source audits: `w2-rules-compendium.md`
