---
id: '0155'
title: Spoken Reaction Interrupts and Ready-Action Combat Triggers
status: Complete
created: 2026-09-26
dependencies:
- TASK-0002
- TASK-0013
- TASK-0022
governing_adrs:
- ADR-0002
- ADR-0006
- ADR-0007
- ADR-0011
governing_prds:
- PRD-0001
governing_stories:
- US-0023
target_release: 0.6.0
pr_url: https://github.com/tyevans/runefoble/pull/171
---
# TASK-0155: Spoken Reaction Interrupts and Ready-Action Combat Triggers

## Status
Refined

## Summary
Implement the reaction interrupt engine and ready-action conditional registry within `services/the_watcher/` and `services/game_session/`, allowing players to halt ongoing turn execution via spoken reaction keywords ("Shield!", "Counterspell!", "Opportunity Attack!") or declare conditional triggers that fire automatically when combat triggers are met.

## Problem Statement
In fast-paced tabletop combat, turn-based systems often force rigid sequential execution where players cannot interject when an enemy acts. To realize the vision of "speak and the board obeys", the engine must pause active turn execution within 500ms of a verbal reaction phrase, prompt the reacting player for confirmation, and evaluate registered ready-actions.

## Governing Architecture & ADRs
- **ADR-0002: Event-Driven Watcher Gameplay Orchestration**: Sub-500ms pipeline pause and intent evaluation.
- **ADR-0006: Redis Streams Event Streaming**: Real-time broadcast of reaction interrupt requests and trigger events.
- **ADR-0007: Domain-Driven Design Architecture**: Clean aggregate state modeling for conditional combat triggers.
- **ADR-0011: eventsource-py Core Event Sourcing**: Event-sourced `TurnReactionDeclared` and `ReadyActionTriggered` events.

## Product & User Story References
- **Product Requirement**: [`prd-0001-the-watcher-ai-dm-and-board-animator.md`](../../product/accepted/prd-0001-the-watcher-ai-dm-and-board-animator.md)
- **User Story**: [`us-0023-spoken-reaction-interrupts-and-ready-actions.md`](../../user_stories/accepted/us-0023-spoken-reaction-interrupts-and-ready-actions.md)

## Detailed Specification & Implementation Plan
1. **Reaction Intent Grammar & Extraction (`services/the_watcher/src/the_watcher/intent/reactions.py`)**:
   - Parse spoken reaction triggers ("I cast Shield", "Counterspell", "Opportunity attack on the goblin") (< 140 lines).
2. **Turn Interruption Coordinator (`services/game_session/src/game_session/reactions/interrupt_coordinator.py`)**:
   - Temporarily pause active turn timer, emit `combat.turn.paused_for_reaction` CloudEvent, and initiate reaction window (< 150 lines).
3. **Ready-Action Conditional Registry (`services/game_session/src/game_session/reactions/ready_action_registry.py`)**:
   - Register conditional triggers (e.g. enemy enters cell range, enemy casts spell) and evaluate conditions against incoming board/combat events (< 160 lines).
4. **CloudEvents Schema Registration (`libs/runefoble_events/src/runefoble_events/combat_reactions.py`)**:
   - Define `CombatTurnPausedForReactionEvent`, `ReactionResolvedEvent`, `ReadyActionRegisteredEvent`, and `ReadyActionTriggeredEvent` (< 110 lines).
5. **Frontdoor API Endpoints (`services/game_session/src/game_session/routers/reactions.py`)**:
   - `POST /sessions/{session_id}/reactions/declare`: Declare reaction interrupt.
   - `POST /sessions/{session_id}/reactions/ready-action`: Register ready-action trigger.
   - `POST /sessions/{session_id}/reactions/{reaction_id}/resolve`: Resolve or dismiss reaction.

## INVEST Criteria Evaluation
- **Independent (I)**: Integrates into turn order without breaking standard turn advancement.
- **Negotiable (N)**: Reaction timeout duration and prompt dismiss rules are configurable.
- **Valuable (V)**: Brings table-like fluid dynamic reactions to digital tabletop combat.
- **Estimable (E)**: Event-driven trigger matching and turn state pausing.
- **Small (S)**: Bounded to reaction coordinator and grammar; all files < 180 lines.
- **Testable (T)**: Frontdoor blackbox tests verify HTTP reaction endpoints and CloudEvent emission.

## Definition of Done (Hard Invariant 7: Blackbox TDD with Frontdoor Setup)
1. **Event-Sourced Engine**:
   - Reaction triggers and turn pausing fully event-sourced with `eventsource-py`.
   - All modules strictly < 190 lines per Hard Invariant 6.
2. **Frontdoor Test Verification**:
   - Blackbox test suite `tests/test_blackbox_reactions/` tests pause, ready-action trigger firing, and turn resumption strictly through HTTP endpoints and Redis Streams events.
3. **Quality Gates**:
   - Passes `uv run pytest tests/test_blackbox_reactions/`, `uv run ruff check .`, and `uv run ruff format --check .`.
