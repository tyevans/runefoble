---
id: 0055
title: Stand-In Policy Guardrails and Mid-Session Hot-Swap Takeover
status: Proposed
created: 2026-09-25
dependencies: [TASK-0003, TASK-0011, TASK-0022]
governing_adrs: [ADR-0002, ADR-0011]
target_release: 0.2.1
---

# TASK-0055: Stand-In Policy Guardrails and Mid-Session Hot-Swap Takeover

## Status
Proposed

## Summary
Add customizable tactical guardrail profiles and seamless mid-session hot-swap takeover mechanics for absent players (Sarah) in `services/the_watcher` and `services/game_session`.

## Problem Statement
Absent players currently rely on static class archetype defaults. They cannot set personal tactical guardrails (e.g. reserving high-level slots or healing specific allies), nor can they smoothly assume direct control mid-encounter if they join late.

## Scope of Work
1. **Guardrail Profile Store**: Store tactical rules (spell slot conservation, ally priorities, risk tolerance) on the character aggregate.
2. **Stand-In Graph Evaluation**: Inject player guardrails into `stand_in_graph.py` prompt context.
3. **Mid-Session Hot-Swap Endpoint**: Add `/api/v1/sessions/{id}/hot-swap` in `game_session` to transition character ownership instantly without resetting turn state.
4. **Permadeath Safeguard**: Add an aggregate invariant ensuring characters under stand-in control stabilize at 0 HP rather than dying permanently.

## Acceptance Criteria
1. Stand-in AI strictly obeys configured spell slot limits and target healing priorities.
2. Hot-swap takeover transfers control in under 100ms over WebSockets without altering initiative order.
3. Automated unit tests verifying permadeath safeguard logic.
