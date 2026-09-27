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
Proposed

## Summary
Build a mobile touch-optimized Lit component in `frontend/` allowing absent players to review their AI stand-in's status, adjust tactical posture directives (Defensive, Cautious, Heroic), and vote on key party decisions with tactile haptic feedback.

## Problem Statement
Absent players currently have no lightweight mobile avenue to steer their stand-in character or cast votes on major long rest or spending decisions without opening a desktop display.

## Governing Architecture & ADRs
- **ADR-0004: Lit + Vite Microfrontends with Storybook**: Mobile subview packaging.
- **ADR-0012: CSS Custom Properties & Semantic Dark/Light Invariants**: Accessible mobile touch targets.
- **ADR-0013: Modular Microfrontend Decomposition**: Component subviews < 200 lines.

## Scope of Work
1. **Directive Stance Selector**:
   - Touch-friendly carousel allowing one-tap selection of character tactical guardrails.
2. **Remote Vote Card with Haptic Trigger**:
   - Card modal rendering active party decision polls with Web Vibration API pulse feedback.
3. **Frontdoor Verification**:
   - Component unit tests and Storybook touch interaction scenarios.

## Definition of Done
- Component implemented in `frontend/src/components/companion/`.
- Haptic vibrations fire on vote submission and urgent alerts.
- Storybook stories render without errors.
- Component length remains under 200 lines.
