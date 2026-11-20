---
id: 0017
title: Human DM Veto and Private Narrative Co-Pilot Whispers
status: Accepted
created: 2026-09-25
governing_prd: PRD-0001
persona: Evelyn (DM)
---

# US-0017 — Human DM Veto and Private Narrative Co-Pilot Whispers

## Governing PRD
- [`PRD-0001: The Watcher AI Dungeon Master and Real-Time Board Animator`](../../product/accepted/prd-0001-the-watcher-ai-dm-and-board-animator.md)

## User Story

**As an** overworked human Dungeon Master (Evelyn),  
**I want to** receive private atmospheric hints and have instant veto/override power over AI DM rulings,  
**So that** The Watcher acts as my supportive co-pilot without undermining my creative authority or spoiling narrative secrets.

## Acceptance Criteria

1. **Private Co-Pilot Whispers**: The Watcher streams private narrative cues (secret NPC motivations, sensory details, perception checks) visible only to the DM.
2. **One-Click Veto**: The DM interface provides an instant "Veto" and "Edit" action on any generated AI action or monster movement before it commits to the board.
3. **Non-Blocking Fallback**: When the DM overrides an AI action, the system halts autonomous execution and yields turn arbitration immediately to the human DM.
4. **WebSocket Privacy**: Whispers and pending uncommitted AI suggestions are encrypted or filtered from player and spectator WebSocket channels.

## Release One Behaviour (TASK-0949)

- The whispers come only from the language model, through the narration port of The Watcher. A new session has no whispers. With no model configured, the whisper bar says "No language model is configured for whispers." and shows no invented text.
- The Veto button calls `POST /api/v1/watcher/veto` through the gateway. A vetoed action does not run when the pause window ends.
- Approve and Edit send their events, but the App Shell does not handle them yet.

## BDD Scenarios

The executable form is `e2e/features/dm_whispers_and_veto.feature`. The veto scenario proposes the AI action with the public route `POST /api/v1/watcher/actions/propose` and the DM's token (DoR item 8).

```gherkin
Scenario: Without a language model the whisper bar says so and shows no invented text
  Given the stack has no language model for narration
  When Evelyn runs the active session "Whisper Night" in the UI
  Then Evelyn's whisper bar shows "No language model is configured for whispers."
  And Evelyn's whisper bar shows no whisper

Scenario: With a language model the DM sees a whisper that the model wrote
  Given the stack has a language model for narration
  And Evelyn runs the active session "Whisper Night" in the UI
  When Evelyn asks for a whisper in the whisper bar
  Then Evelyn's whisper bar shows the model whisper that the gateway lists

Scenario: The DM vetoes a pending AI action and it does not run
  Given The Watcher proposes "The goblin runs to the door" for "Whisper Night" with a 45 second pause window
  And Evelyn runs the active session "Whisper Night" in the UI
  When Evelyn clicks Veto on the pending action in the whisper bar
  Then Evelyn's whisper bar shows the action as vetoed
  And after the pause window the action is still vetoed
```
