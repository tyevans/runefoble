---
id: '0055'
title: Stand-In Policy Guardrails and Mid-Session Hot-Swap Takeover
status: Refined
created: 2026-09-25
dependencies:
- TASK-0003
- TASK-0011
- TASK-0022
governing_adrs:
- ADR-0001
- ADR-0002
- ADR-0011
- ADR-0013
target_release: 0.2.1
---

# TASK-0055: Stand-In Policy Guardrails and Mid-Session Hot-Swap Takeover

## Status
Refined

## Summary
Add customizable tactical guardrail profiles and seamless mid-session hot-swap takeover mechanics for absent players in `services/the_watcher`, `services/character_sheet`, and `services/game_session`.

## Problem Statement
Missing players currently rely on static class archetype behaviors. They cannot declare personal tactical guardrails (e.g. reserving 3rd-level spell slots, prioritizing healing the rogue, or avoiding melee engagements) before an absence (PRD-0002, US-0025). Furthermore, when an absent player logs in late mid-encounter, there is no smooth mechanism to hot-swap control from the AI stand-in without disrupting the active turn order (US-0026). A critical permadeath safeguard is also missing: AI stand-ins should stabilize at 0 HP rather than facing irreversible character death while under automated control.

## Governing Architecture & ADRs
- **ADR-0001**: SpiceDB Zanzibar Object Authorization (ownership handover between AI stand-in and player user identity).
- **ADR-0002**: The Watcher Autonomous DM (stand-in persona emulation and tactical decision boundaries).
- **ADR-0011**: eventsource-py Core Event Sourcing (`StandInPolicyUpdated`, `CharacterControlTransferred`, `StandInStabilized`).
- **ADR-0013**: Microfrontend Architecture and Service Component Vendoring (`services/character_sheet/ui/`).

## Product & User Story References
- **Product Requirement**: [`prd-0002-missing-player-ai-stand-in-with-penalties.md`](../../product/accepted/prd-0002-missing-player-ai-stand-in-with-penalties.md)
- **User Stories**:
  - [`us-0025-personalized-ai-stand-in-tactical-policies.md`](../../user_stories/accepted/us-0025-personalized-ai-stand-in-tactical-policies.md)
  - [`us-0026-mid-session-hot-swap-takeover-and-permadeath-lock.md`](../../user_stories/accepted/us-0026-mid-session-hot-swap-takeover-and-permadeath-lock.md)

## Scope of Work
1. **Character Tactical Guardrail Schema**:
   - Add `stand_in_guardrails` model to character sheet aggregate: spell slot preservation limits, party member protection affinities, and risk threshold flags.
2. **Stand-In Graph Policy Evaluation**:
   - Incorporate guardrails into `stand_in_graph.py` prompt context and action selection logic.
3. **Mid-Session Hot-Swap API**:
   - Provide `POST /api/v1/sessions/{id}/hot-swap` in `game_session` transferring active token and turn control from AI to player in < 100ms.
4. **Zero-HP Permadeath Safeguard**:
   - Enforce an aggregate invariant: when damage reduces a stand-in character to 0 HP, automatically stabilize or trigger unconciousness without death save failures.
5. **Frontdoor Blackbox Verification**:
   - Comprehensive test suite in `tests/test_blackbox_stand_in_guardrails.py`.

## INVEST Criteria Evaluation
- **Independent (I)**: Operates within existing character sheet and session state machines without external service blocking.
- **Negotiable (N)**: Guardrail policy options can be extended over time.
- **Valuable (V)**: Protects absent players from devastating outcomes and removes session start anxiety (core platform value).
- **Estimable (E)**: Directly extends existing stand-in engine (TASK-0003) and initiative tracker (TASK-0022).
- **Small (S)**: Scope strictly isolated to character sheet, session, and watcher endpoints; all files < 250 lines.
- **Testable (T)**: Verifiable via public HTTP API routes and WebSocket turn broadcasts.

## Definition of Done (Hard Invariant 7: Blackbox TDD with Frontdoor Setup)
1. **Public HTTP Frontdoor API**:
   - `PUT /api/v1/characters/{id}/guardrails`: Configures tactical constraints for stand-in AI.
   - `POST /api/v1/sessions/{id}/hot-swap`: Hands off active turn control from AI stand-in to authenticating player.
2. **Domain Event Publication**:
   - Emits `StandInPolicyUpdated` and `CharacterControlTransferred` CloudEvents over Redis Streams.
3. **Permadeath Safeguard Invariant**:
   - Unit and blackbox assertions verify stand-in character stabilizes at 0 HP.
4. **Frontdoor Blackbox Test Suite**:
   - `tests/test_blackbox_stand_in_guardrails.py` verifying guardrail enforcement, live hot-swap, and zero-HP stabilization.
5. **Quality Gates**:
   - Conforms strictly to Hard Invariant 6 (< 500 lines per file).
   - Passes `uv run pytest tests/test_blackbox_stand_in_guardrails.py` and `uv run ruff check`.
