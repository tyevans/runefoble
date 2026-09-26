---
id: '0054'
title: Conversational Disambiguation and Compound Action Intents
status: Complete
created: 2026-09-25
dependencies:
- TASK-0002
- TASK-0027
governing_adrs:
- ADR-0002
- ADR-0006
- ADR-0007
- ADR-0011
target_release: 0.2.1
pr_url: https://github.com/tyevans/runefoble/pull/71
---
# TASK-0054: Conversational Disambiguation and Compound Action Intents

## Status
Refined

## Summary
Extend `services/the_watcher` intent parsing and action execution to support multi-part tactical combos and conversational target disambiguation for voice-driven players.

## Problem Statement
When a player speaks an ambiguous command (*"I shoot the goblin"* when three goblins are on the grid) or a compound action (*"I jump over the pit and attack the necromancer with my greataxe"*), the single-shot intent parser either fails or guesses arbitrarily (PRD-0001, US-0021). The platform requires conversational disambiguation prompts that clarify intent in under 400ms and decompose compound utterances into chained action graphs without desynchronizing combat state.

## Governing Architecture & ADRs
- **ADR-0002**: The Watcher Autonomous DM (natural speech parsing and intent extraction).
- **ADR-0006**: Redis Streams Event Bus Transport (`IntentDisambiguationRequested`, `CompoundActionResolved`).
- **ADR-0007**: Real-Time Voice and Board Synchronization (sub-500ms pipeline budget).
- **ADR-0011**: eventsource-py Core Event Sourcing (sequential aggregate state mutators).

## Product & User Story References
- **Product Requirement**: [`prd-0001-the-watcher-ai-dm-and-board-animator.md`](../../product/accepted/prd-0001-the-watcher-ai-dm-and-board-animator.md), [`prd-0013-immersive-and-intuitive-frontend-experience.md`](../../product/accepted/prd-0013-immersive-and-intuitive-frontend-experience.md)
- **User Story**: [`us-0021-conversational-intent-disambiguation-and-combos.md`](../../user_stories/accepted/us-0021-conversational-intent-disambiguation-and-combos.md)

## Scope of Work
1. **Target Disambiguation Engine**:
   - Detect ambiguous entity references using spatial coordinates and entity tags from `board_state`.
   - Generate audio/text clarification prompts (*"Which goblin? The archer by the pillar or the shaman on the altar?"*).
2. **Compound Action Chaining**:
   - Parse multi-clause utterances into sequential sub-action nodes (e.g. `[Move(target=(5,7)), SkillCheck(Athletics), Attack(Necromancer)]`).
   - Coordinate rollback or partial success if an intermediate action fails (e.g., athletics check fails mid-jump).
3. **Ghost Preview Event Integration**:
   - Emit preview path candidates over Redis Streams during clarification to highlight candidate targets on the board.
4. **Frontdoor Blackbox Verification**:
   - Comprehensive test suite in `tests/test_blackbox_intent_disambiguation.py`.

## INVEST Criteria Evaluation
- **Independent (I)**: Enhances intent parsing and graph orchestration without altering physical grid coordinate rules.
- **Negotiable (N)**: Clarification phrase templates and disambiguation timeout can be adjusted.
- **Valuable (V)**: Eliminates voice friction for players, fulfilling core natural voice game premise.
- **Estimable (E)**: Builds on existing `speech_to_intent.py` and `stand_in_graph.py` foundations.
- **Small (S)**: Scope strictly isolated to `services/the_watcher`; all new modules < 250 lines.
- **Testable (T)**: Tested via public `/api/v1/watcher/intent/parse` and `/api/v1/watcher/intent/resolve` endpoints.

## Definition of Done (Hard Invariant 7: Blackbox TDD with Frontdoor Setup)
1. **Public HTTP Frontdoor API**:
   - `POST /api/v1/watcher/intent/parse`: Parses audio transcript, returning either executable action plan or `requires_disambiguation=True` with candidate target options.
   - `POST /api/v1/watcher/intent/resolve`: Submits player disambiguation choice and emits resolved compound action graph.
2. **Timing Budget Compliance**:
   - Disambiguation candidate evaluation executes in < 400ms.
3. **CloudEvents Publication**:
   - Emits `IntentDisambiguationRequested` and `CompoundActionResolved` over Redis Streams.
4. **Frontdoor Blackbox Test Suite**:
   - `tests/test_blackbox_intent_disambiguation.py` verifying multi-target clarification, combo ordering, and partial failure handling.
5. **Quality Gates**:
   - Conforms strictly to Hard Invariant 6 (< 500 lines per file).
   - Passes `uv run pytest tests/test_blackbox_intent_disambiguation.py` and `uv run ruff check`.
