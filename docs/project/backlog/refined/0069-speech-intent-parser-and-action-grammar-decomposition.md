---
id: '0069'
title: Speech Intent Parser and Action Grammar Extractors Modular Decomposition
status: Refined
created: 2026-09-26
dependencies:
- TASK-0002
- TASK-0039
governing_adrs:
- ADR-0002
- ADR-0003
target_release: 0.2.0
governing_prds:
- PRD-0001
governing_stories:
- US-0001
- US-0021
---

# TASK-0069: Speech Intent Parser and Action Grammar Extractors Modular Decomposition

## Status
Refined

## Summary
Decompose `services/the_watcher/src/the_watcher/movement_parser.py` (327 lines, 65.4% of limit) into modular submodules (`grammars.py`, `spatial.py`, and `movement_parser.py`) to prevent breaching Hard Invariant 6 (File length limit < 500 lines) as streaming Whisper VAD integration (TASK-0039) and conversational disambiguation with compound intents (TASK-0054) are incorporated.

## Problem Statement
`services/the_watcher/src/the_watcher/movement_parser.py` combines multiple disparate concerns in a single module:
1. Complex regular expression patterns for natural language grammar matching (coordinate movement, distance/direction cardinal parsing, flanking syntax, spellcasting invocations, token targeting, attack weapons, skills, death saving throws, and dice rolls).
2. Tactical spatial grid calculations (`compute_directional_deltas`, `calculate_steps`, `calculate_bounded_destination`).
3. Intent routing and extraction (`parse_speech_intent`) dispatching across eight distinct action types (`move`, `flank`, `cast_spell`, `attack`, `check`, `roll`, `death_save`, `unknown`) and generating Watcher atmospheric flavor replies.

As streaming Whisper transcription and compound multi-action intents are integrated, this parser will rapidly surpass 500 lines unless decoupled into focused modules.

## Governing Architecture & ADRs
- **ADR-0002: Realtime Voice and Board Sync**: Sub-500ms speech-to-intent pipeline execution without blocking audio threads.
- **ADR-0003: UV Monorepo Workspace for Python BCs**: Clean modular decomposition inside `services/the_watcher/`.

## Product & User Story References
- **Product Requirement**: [`prd-0001-the-watcher-ai-dm-and-board-animator.md`](../../product/accepted/prd-0001-the-watcher-ai-dm-and-board-animator.md)
- **User Stories**:
  - [`us-0001-player-commands-board-via-voice.md`](../../user_stories/accepted/us-0001-player-commands-board-via-voice.md)
  - [`us-0021-conversational-intent-disambiguation-and-combos.md`](../../user_stories/accepted/us-0021-conversational-intent-disambiguation-and-combos.md)

## Detailed Specification & Implementation Plan
1. **Action Grammar Patterns (`services/the_watcher/src/the_watcher/grammars.py`)**:
   - Extract compiled regular expressions and lexical token sets for movement, attacks, spellcasting, skill checks, and dice rolls (< 100 lines).
2. **Tactical Spatial Math (`services/the_watcher/src/the_watcher/spatial.py`)**:
   - Extract `compute_directional_deltas`, `calculate_steps`, and `calculate_bounded_destination` grid bounding logic (< 80 lines).
3. **Intent Parser Coordinator (`services/the_watcher/src/the_watcher/movement_parser.py`)**:
   - Retain `SpeechIntentParser` orchestrating grammar matchers and spatial calculations, producing `IntentResult` instances while maintaining 100% backward-compatible public methods (< 180 lines).

## INVEST Criteria Evaluation
- **Independent (I)**: Refactors internal parser implementation without altering public FastAPI endpoints or `IntentResult` contracts.
- **Negotiable (N)**: Submodule naming and grammar groupings can be adjusted.
- **Valuable (V)**: Protects against Hard Invariant 6 violations (< 500 lines) in The Watcher core speech-to-intent engine.
- **Estimable (E)**: Pure refactoring separating regex grammar compilation and grid math from intent result construction.
- **Small (S)**: Scope strictly isolated to `services/the_watcher/src/the_watcher/`; all resulting files < 190 lines.
- **Testable (T)**: Existing test suites verify 100% identical intent parsing accuracy.

## Definition of Done (Hard Invariant 7: Blackbox TDD with Frontdoor Setup)
1. **Zero Breaking Changes**:
   - Public APIs of `SpeechIntentParser` and `IntentResult` structures remain fully preserved.
2. **Strict Line Limit Enforced**:
   - All modified and newly authored files strictly under 200 lines in compliance with Hard Invariant 6.
3. **Frontdoor Test Verification**:
   - 100% test pass rate on `uv run pytest tests/test_speech_to_intent.py tests/test_movement_parser.py tests/test_blackbox_the_watcher.py`.
4. **Quality Gates**:
   - Passes `uv run ruff check` and `uv run ruff format --check`.
