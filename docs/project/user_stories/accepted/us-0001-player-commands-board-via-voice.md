---
id: 0001
title: Spoken Tactical Board Manipulation
status: Accepted
created: 2026-09-25
governing_prd: PRD-0001
persona: Marcus (Adventurer)
---

# US-0001 — Spoken Tactical Board Manipulation

## Governing PRD
- [`PRD-0001: The Watcher AI Dungeon Master and Real-Time Board Animator`](../../product/accepted/prd-0001-the-watcher-ai-dm-and-board-animator.md)

## User Story

**As a** tabletop player in an active encounter,
**I want to** speak naturally to move my character token across the tactical map ("Valeros strides three squares forward"),
**So that** I stay immersed in the collaborative story without breaking eye contact or fumbling with map coordinates.

## Acceptance Criteria

1. **Natural Speech Recognition**: Spoken phrases stating direction and distances (e.g., "charge 2 spaces east", "fall back 1 square south") are correctly transcribed and parsed.
2. **Visual Feedback**: The tactical board highlights the token, moves it to the target cell, and updates fog-of-war within 500ms.
3. **Turn Validation**: If it is not the player's turn, or the move exceeds movement speed, The Watcher gently prompts the player or queues the intent.
4. **Narrative Chronicle**: The action is broadcast over WebSockets and added to the collaborative chronicle feed.
5. **Typed Command** (TASK-0945, PRD-0025): The player can type the same command in the command bar of the session view. The board shows the move as a ghost preview, and the token moves only when the player confirms it. A transcript that The Watcher does not parse stages no preview. A failed call shows its status and detail in the bar, and the typed text stays.

## Acceptance Scenarios

Executable in `e2e/features/voice_typed_command.feature`. The setup uses the UI and public gateway routes only (ADR-0014).

```gherkin
Scenario: A typed move stages a ghost preview that the player confirms
  When Valeros drags his token "Valeros the Bold" to coordinate (3, 3)
  Then the token "Valeros the Bold" is at (3, 3) on both screens
  When Valeros types "move 2 squares west" in the command bar and presses Enter
  Then the ghost banner on both screens says "Valeros the Bold" moves to (1, 3)
  And the token "Valeros the Bold" is at (3, 3) on both screens
  When Valeros confirms the ghost preview
  Then the token "Valeros the Bold" is at (1, 3) on both screens

Scenario: A transcript that the grammar does not parse stages no preview
  When Valeros types "dance nicely" in the command bar and presses Enter
  Then the command bar answers the command
  And no ghost banner appears on Valeros's screen

Scenario: The command bar shows the error when The Watcher is down
  Given The Watcher service is stopped
  When Valeros types "move 2 squares south" in the command bar and presses Enter
  Then the command bar shows an error with status 503
  And the command bar keeps the text "move 2 squares south"
```
