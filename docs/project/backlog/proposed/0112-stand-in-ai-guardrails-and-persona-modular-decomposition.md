---
id: '0112'
title: Stand-In AI Persona Decision Engine and Tactical Policy Modular Decomposition
status: Proposed
created: 2026-09-26
dependencies:
- TASK-0003
- TASK-0055
governing_adrs:
- ADR-0002
- ADR-0003
- ADR-0006
target_release: 0.3.0
governing_prds:
- PRD-0002
governing_stories:
- US-0004
- US-0005
- US-0025
---

# TASK-0112: Stand-In AI Persona Decision Engine and Tactical Policy Modular Decomposition

## Status
Proposed

## Summary
Decompose `services/the_watcher/src/the_watcher/stand_in_ai.py` (344 lines, 68.8% of limit) into specialized policy, persona, and chronicle recap sub-modules to prevent breaching Hard Invariant 6 (File length limit < 500 lines) as autonomous tactical combat actions and advanced multi-class stand-in behaviors expand.

## Problem Statement
`services/the_watcher/src/the_watcher/stand_in_ai.py` currently consolidates three distinct behavioral domains into a single monolithic class:
1. Tactical guardrail policies: Evaluating ally protection, melee avoidance, spell slot preservation, and 0-HP stabilization priorities.
2. Character persona & penalty simulation: Injecting humorous DM-inflicted penalties (`drunk`, `foolishness`, `cowardice`, `greed`) into dialogue, dice formulas, and flavor actions.
3. Absentee chronicle recap generation: Producing multi-paragraph narrative summaries of absent character actions and comedic mishaps for session chronicles.

As Milestone 5 and 6 introduce autonomous NPC factions and deeper party tactics, this engine will grow beyond 500 lines unless decoupled into focused sub-modules.

## Proposed Decomposition
1. **Tactical Guardrails Evaluator (`services/the_watcher/src/the_watcher/stand_in_guardrails.py`)**:
   - `evaluate_tactical_guardrails`: Ally protection matching, melee distance heuristics, spell slot preservation checks, and triage logic (< 140 lines).
2. **Persona & Penalty Simulator (`services/the_watcher/src/the_watcher/stand_in_persona.py`)**:
   - `apply_penalty_modifiers`: Dialogue flavor injection, disadvantage formulas, and personality trait weighting (< 140 lines).
3. **Chronicle Recap Generator (`services/the_watcher/src/the_watcher/stand_in_recap.py`)**:
   - `generate_absentee_recap`: Chronicle paragraph construction, comedic excuse formatting, and MVP highlight extraction (< 110 lines).
4. **Primary Engine Facade (`services/the_watcher/src/the_watcher/stand_in_ai.py`)**:
   - Lightweight `StandInAIEngine` delegating to guardrail, persona, and recap evaluators (< 80 lines).

## INVEST Criteria Evaluation
- **Independent (I)**: Refactors internal engine mechanics without changing `StandInAction` schemas or API contracts.
- **Negotiable (N)**: Organization of penalty dialogue templates can be adjusted.
- **Valuable (V)**: Protects against Hard Invariant 6 violations (< 500 lines) and enables unit testing of tactical policies independent of dialogue generation.
- **Estimable (E)**: Clean Python class and helper function extraction.
- **Small (S)**: Scope strictly isolated to `services/the_watcher/src/the_watcher/stand_in_ai.py`; all resulting modules < 150 lines.
- **Testable (T)**: Verified with `uv run pytest tests/test_stand_in_engine.py tests/test_blackbox_stand_in_guardrails.py`.

## Acceptance Criteria
1. `services/the_watcher/src/the_watcher/stand_in_ai.py` decomposed into modular files under 150 lines each.
2. 100% test pass rate across all stand-in tactical, penalty, and recap test cases.
3. Preserves existing `StandInAIEngine` public interface and behavior.
4. Conforms strictly to Hard Invariant 6 (< 500 lines per file).
