---
id: '0167'
title: Absentee Mobile Directive and Remote Voting Microfrontend
status: Proposed
created: 2026-09-26
dependencies:
- TASK-0134
- TASK-0151
governing_adrs:
- ADR-0004
- ADR-0012
- ADR-0013
governing_prds:
- PRD-0019
governing_stories:
- US-0059
- US-0027
target_release: 0.7.0
---

# TASK-0167: Absentee Mobile Directive and Remote Voting Microfrontend

## Status
Refined

## Summary
Build a mobile touch-optimized Lit Web Component in `services/the_watcher/ui/` (`<runefoble-absentee-directive>`) allowing absent players to review their AI stand-in's status, adjust tactical posture directives (Defensive, Cautious, Heroic), and vote on key party decisions with tactile haptic feedback.

## Problem Statement
Absent players currently have no lightweight mobile interface to inspect or steer their stand-in character's tactical posture or cast votes on major long rest and treasure decisions without opening the full desktop VTT application.

## Governing Architecture & ADRs
- **ADR-0004: Lit + Vite Microfrontends with Storybook**: Mobile subview packaging with Shadow DOM encapsulation.
- **ADR-0012: CSS Custom Properties & Semantic Dark/Light Invariants**: Accessible mobile touch targets and Bauhaus semantic tokens.
- **ADR-0013: Modular Microfrontend Decomposition**: Component subviews and styles kept strictly < 160 lines.

## Product & User Story References
- **Product Requirement**: [`prd-0019-spatial-companion-mobile-and-haptic-ping-gateway.md`](../../product/accepted/prd-0019-spatial-companion-mobile-and-haptic-ping-gateway.md)
- **User Story**: [`us-0059-spatial-companion-mobile-and-haptic-ping-gateway.md`](../../user_stories/accepted/us-0059-spatial-companion-mobile-and-haptic-ping-gateway.md)
- **User Story**: [`us-0027-absentee-character-resource-ledger-and-recap-reel.md`](../../user_stories/accepted/us-0027-absentee-character-resource-ledger-and-recap-reel.md)

## Detailed Specification & Implementation Plan
1. **Directive Stance Selector Custom Element (`services/the_watcher/ui/src/runefoble-absentee-directive.ts`)**:
   - Touch-friendly carousel allowing one-tap selection of character tactical guardrails (Defensive, Balanced, Aggressive) (< 150 lines).
2. **Remote Vote Card & Haptic Trigger (`services/the_watcher/ui/src/runefoble-absentee-vote-card.ts`)**:
   - Card modal rendering active party decision polls with Web Vibration API pulse feedback (< 130 lines).
3. **Styles & Semantic Design Tokens (`services/the_watcher/ui/src/runefoble-absentee-directive.styles.ts`)**:
   - Responsive CSS layout optimized for mobile portrait viewports with AA contrast compliance (< 110 lines).
4. **Storybook Stories (`services/the_watcher/ui/src/runefoble-absentee-directive.stories.ts`)**:
   - Interactive touch interaction scenarios and light/dark theme demonstrations (< 120 lines).

## INVEST Criteria Evaluation
- **Independent (I)**: Functions on mobile companion browsers without requiring the full tactical board engine.
- **Negotiable (N)**: Posture preset definitions and voting timer thresholds can be customized.
- **Valuable (V)**: Keeps absent players actively engaged with the session outcome from anywhere on their phone.
- **Estimable (E)**: Standard Lit custom elements communicating with existing Watcher stand-in APIs.
- **Small (S)**: Bounded strictly to `services/the_watcher/ui/`; all files < 160 lines.
- **Testable (T)**: Frontdoor blackbox tests verify UI manifest inclusion, attribute updates, and custom DOM event dispatch.

## Definition of Done (Hard Invariant 7: Blackbox TDD with Frontdoor Setup)
1. **Microfrontend Architecture**:
   - Component created in `services/the_watcher/ui/` with Shadow DOM and manifest registration.
   - All component files strictly < 160 lines per Hard Invariant 6.
2. **Frontdoor Test Verification**:
   - Blackbox test suite `tests/test_blackbox_absentee_directive_ui/` asserts manifest exposure and stance selection dispatch.
3. **Quality Gates**:
   - Storybook renders with zero console errors.
   - Passes `uv run pytest tests/test_blackbox_absentee_directive_ui/`, `uv run ruff check .`, and `uv run ruff format --check .`.
