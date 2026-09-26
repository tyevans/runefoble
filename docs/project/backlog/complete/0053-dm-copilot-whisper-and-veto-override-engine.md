---
id: '0053'
title: DM Co-Pilot Whisper Prompts and Veto Override Engine
status: Complete
created: 2026-09-25
dependencies:
- TASK-0002
- TASK-0013
- TASK-0016
governing_adrs:
- ADR-0001
- ADR-0002
- ADR-0004
- ADR-0007
- ADR-0013
target_release: 0.2.1
pr_url: https://github.com/tyevans/runefoble/pull/72
---
# TASK-0053: DM Co-Pilot Whisper Prompts and Veto Override Engine

## Status
Refined

## Summary
Implement private DM whisper channels and instant veto/override mechanics in `services/the_watcher` and the frontend, allowing human DMs to review, edit, or veto AI-proposed actions before they execute on the tactical board.

## Problem Statement
ADR-0002 mandates that "The Watcher is an assistant, never a dictator." Currently, when The Watcher proposes narrative developments, NPC actions, or secret perception checks, it either announces them openly or acts automatically. Human DMs (Evelyn) require a private whisper channel and an action interceptor window allowing one-click veto, edit, or approval before board state mutates (PRD-0001, US-0017).

## Governing Architecture & ADRs
- **ADR-0001**: SpiceDB Zanzibar Object Authorization (enforcing `dm` permission on whisper streams and action veto overrides).
- **ADR-0002**: The Watcher Autonomous DM (human DM veto primacy and assistive intent generation).
- **ADR-0004**: Lit Web Components & Storybook UI (`<runefoble-dm-whisper-bar>`).
- **ADR-0007**: Real-Time Voice and Board Synchronization (low-latency veto event broadcasting).
- **ADR-0013**: Microfrontend Architecture and Service Component Vendoring (`services/the_watcher/ui/`).

## Product & User Story References
- **Product Requirement**: [`prd-0001-the-watcher-ai-dm-and-board-animator.md`](../../product/accepted/prd-0001-the-watcher-ai-dm-and-board-animator.md)
- **User Story**: [`us-0017-human-dm-veto-and-narrative-copilot-whispers.md`](../../user_stories/accepted/us-0017-human-dm-veto-and-narrative-copilot-whispers.md)

## Scope of Work
1. **Private Whisper Channel**:
   - Add secure DM narrative suggestion stream in `the_watcher` emitting atmospheric hints, monster tactics, and passive perception alerts.
   - Restrict whisper payloads strictly to users with `dungeon_master` relation in SpiceDB.
2. **Pre-Execution Veto Interceptor**:
   - Introduce a configurable pre-execution pause window (default 2000ms) for AI-proposed game mutations.
   - Expose veto/approve/modify API endpoints in `the_watcher` modular routers.
3. **Frontend DM Whisper Bar Component**:
   - Implement `<runefoble-dm-whisper-bar>` Lit component in `services/the_watcher/ui/src/`.
   - Provide one-click actions: "Approve", "Veto", "Edit Intent".
4. **Frontdoor Blackbox Verification**:
   - Write comprehensive blackbox test suite in `tests/test_blackbox_dm_copilot.py`.

## INVEST Criteria Evaluation
- **Independent (I)**: Intercepts Watcher proposed actions without altering underlying board aggregate mutations.
- **Negotiable (N)**: Pause window duration and whisper UI styling can be configured per campaign.
- **Valuable (V)**: Guarantees human DM authority and narrative veto, realizing core principle of ADR-0002.
- **Estimable (E)**: Builds directly on existing Watcher routers and WebSocket permission checks (TASK-0016).
- **Small (S)**: Scope strictly isolated to `services/the_watcher` and its microfrontend; all files < 250 lines.
- **Testable (T)**: Tested via public WebSocket events and HTTP endpoints with SpiceDB role fixtures.

## Definition of Done (Hard Invariant 7: Blackbox TDD with Frontdoor Setup)
1. **Zanzibar Authorization Enforcement**:
   - Whispers and veto endpoints reject non-DM users with 403 Forbidden via SpiceDB Zanzibar checks.
2. **Public Frontdoor APIs**:
   - `POST /api/v1/watcher/veto`: Cancels pending action execution and emits `WatcherActionVetoed`.
   - `POST /api/v1/watcher/approve`: Commits pending action immediately.
   - `GET /api/v1/watcher/whispers`: Returns paginated DM private narrative suggestions.
3. **Microfrontend & Storybook**:
   - `<runefoble-dm-whisper-bar>` component integrated in `services/the_watcher/ui/` with Storybook stories.
4. **Frontdoor Blackbox Test Suite**:
   - `tests/test_blackbox_dm_copilot.py` verifying veto interception, non-DM rejection, and action resolution.
5. **Quality Gates**:
   - Conforms strictly to Hard Invariant 6 (< 500 lines per file).
   - Passes `uv run pytest tests/test_blackbox_dm_copilot.py` and `uv run ruff check`.
