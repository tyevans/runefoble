---
id: '0069'
title: Speech Intent Parser and Action Grammar Extractors Modular Decomposition
status: Proposed
created: 2026-09-26
dependencies: [TASK-0002, TASK-0039]
governing_adrs: [ADR-0002, ADR-0003]
target_release: 0.2.0
---

# TASK-0069: Speech Intent Parser and Action Grammar Extractors Modular Decomposition

## Status
Proposed

## Summary
Decompose `services/the_watcher/src/the_watcher/movement_parser.py` (327 lines, 65.4% of limit) into modular submodules (`grammars.py`, `spatial.py`, and `movement_parser.py`) to prevent breaching Hard Invariant 6 (File length limit < 500 lines) as streaming Whisper VAD integration (TASK-0039) and conversational disambiguation with compound intents (TASK-0054) are incorporated.

## Problem Statement
`services/the_watcher/src/the_watcher/movement_parser.py` combines multiple disparate concerns in a single module:
1. Complex regular expression patterns for natural language grammar matching (coordinate movement, distance/direction cardinal parsing, flanking syntax, spellcasting invocations, token targeting, attack weapons, skills, death saving throws, and dice rolls).
2. Tactical spatial grid calculations (`compute_directional_deltas`, `calculate_steps`, `calculate_bounded_destination`).
3. Intent routing and extraction (`parse_speech_intent`) dispatching across eight distinct action types (`move`, `flank`, `cast_spell`, `attack`, `check`, `roll`, `death_save`, `unknown`) and generating Watcher atmospheric flavor replies.

As Milestone 2 connects streaming Whisper transcription (TASK-0039) and Milestone 3 adds compound multi-action intents and disambiguation queries (TASK-0054), this parser will rapidly surpass 500 lines unless decoupled into focused modules.

## Proposed Decomposition
1. **Action Grammar Patterns (`services/the_watcher/src/the_watcher/grammars.py`)**:
   - Extract compiled regular expressions and lexical token sets for movement, attacks, spellcasting, skill checks, and dice rolls (< 100 lines).
2. **Tactical Spatial Math (`services/the_watcher/src/the_watcher/spatial.py`)**:
   - Extract `compute_directional_deltas`, `calculate_steps`, and `calculate_bounded_destination` grid bounding logic (< 80 lines).
3. **Intent Parser Coordinator (`services/the_watcher/src/the_watcher/movement_parser.py`)**:
   - Retain `SpeechIntentParser` orchestrating grammar matchers and spatial calculations, producing `IntentResult` instances while maintaining 100% backward-compatible public methods (< 180 lines).

## INVEST Criteria Evaluation
- **Independent (I)**: Refactors internal parser implementation without altering the public FastAPI endpoints or `IntentResult` contract.
- **Negotiable (N)**: Submodule naming and grammar groupings can be adjusted as new grammar forms are added.
- **Valuable (V)**: Protects against Hard Invariant 6 violations (< 500 lines) in The Watcher core speech-to-intent engine.
- **Estimable (E)**: Pure refactoring separating regex grammar compilation and grid math from intent result construction.
- **Small (S)**: Scope strictly isolated to `services/the_watcher/src/the_watcher/`; all resulting files < 190 lines.
- **Testable (T)**: Existing test suites (`tests/test_speech_to_intent.py`, `tests/test_movement_parser.py`) verify 100% identical intent parsing accuracy.

## Acceptance Criteria
1. Zero breaking changes to `SpeechIntentParser` public APIs or `IntentResult` structures.
2. All modified and new files strictly under 200 lines.
3. 100% test pass rate on `uv run pytest tests/test_speech_to_intent.py tests/test_movement_parser.py`.
4. Conforms strictly to Hard Invariant 6 (< 500 lines per file).
