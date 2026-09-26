---
id: 0021
title: Conversational Intent Disambiguation and Multi-Action Combos
status: Accepted
created: 2026-09-25
---

# US-0021 — Conversational Intent Disambiguation and Multi-Action Combos

## User Story

**As a** voice-first martial adventurer (Marcus),  
**I want to** speak natural compound combat actions and have ambiguous targets audibly clarified,  
**So that** I never have to look down at dropdown menus to specify targets or resolve heroic stunts.

## Acceptance Criteria

1. **Target Disambiguation**: When an action is ambiguous ("I attack the cultist" when two exist), The Watcher audibly and visually clarifies ("Cultist with the staff or the dagger?").
2. **Compound Action Decomposition**: Multi-part phrases ("I vault the table and strike the brute") parse into sequential capability checks (Athletics check followed by melee attack).
3. **Conversational Feedback**: The Watcher confirms the resolved sequence in under 500ms before triggering dice and board animation.
