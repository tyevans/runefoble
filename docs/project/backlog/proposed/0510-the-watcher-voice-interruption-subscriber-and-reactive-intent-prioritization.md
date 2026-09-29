---
id: '0510'
title: The Watcher Voice Interruption Subscriber and Reactive Intent Prioritization
status: Proposed
created: 2026-09-29
dependencies:
- TASK-0002
- TASK-0013
- TASK-0141
governing_adrs:
- ADR-0002
- ADR-0006
- ADR-0007
governing_prds:
- PRD-0001
- PRD-0020
governing_stories:
- US-0023
- US-0060
target_release: 0.9.0
---

# TASK-0510: The Watcher Voice Interruption Subscriber and Reactive Intent Prioritization

## Status
Proposed

## Summary
Implement a Redis Streams event subscriber in `services/the_watcher` listening for `VoiceSpeechInterrupted` domain events, immediately signaling the active narrative generator to halt ongoing LLM token streaming and scene narration, archiving unread narration text into the session chronicle transcript buffer, and escalating incoming player intent priority to execute urgent tactical reactions (e.g. Shield, Counterspell, Opportunity Attack) before resuming normal narrative pacing per PRD-0020 and US-0023.

## Problem Statement
When `voice_agent` detects speech barge-in and publishes `VoiceSpeechInterrupted`, `the_watcher` currently does not subscribe to this event. Consequently, The Watcher's LLM generation loops continue processing unprompted narration, queued audio blocks remain in memory, and spoken player reaction intents are queued behind stale narrative generation rather than being immediately adjudicated within the required 200ms reaction window.

## Governing Architecture & ADRs
- **ADR-0002: Event-Driven Watcher Gameplay Orchestration**: Orchestrating reactive tabletop narrative transitions via asynchronous event streams.
- **ADR-0006: Redis Streams Event Bus Architecture**: Subscribing to consumer group events on the `runefoble:events:voice` stream topic.
- **ADR-0007: CloudEvents Domain Event Payloads**: Ingesting standardized `VoiceSpeechInterrupted` CloudEvent payloads.

## Product & User Story References
- [`prd-0001-the-watcher-ai-dm-and-board-animator.md`](../../product/accepted/prd-0001-the-watcher-ai-dm-and-board-animator.md)
- [`prd-0020-zero-latency-neural-voice-duplex-and-interruption.md`](../../product/accepted/prd-0020-zero-latency-neural-voice-duplex-and-interruption.md)
- [`us-0023-spoken-reaction-interrupts-and-ready-actions.md`](../../user_stories/accepted/us-0023-spoken-reaction-interrupts-and-ready-actions.md)
- [`us-0060-zero-latency-neural-voice-duplex.md`](../../user_stories/accepted/us-0060-zero-latency-neural-voice-duplex.md)

## Scope of Work
1. **Watcher Event Consumer (`services/the_watcher/src/the_watcher/subscribers/voice_interruption.py`)**:
   - Register consumer group subscriber for `VoiceSpeechInterrupted` events.
   - Cancel active LLM narrative streaming session for matching `session_id`.
   - Store `remaining_narration_text` and `interrupted_at` in the session's temporary narrative context ledger.
2. **Intent Priority Escalator (`services/the_watcher/src/the_watcher/reactive_routing.py`)**:
   - Provide fast-path intent prioritization when a session is in `interrupted` state:
   - Identify reaction keywords ("Shield", "Counterspell", "Dodge", "Uncanny Dodge").
   - Dispatch immediate combat reaction resolution event to `game_session` within < 100ms.
3. **Resumption & Narrative Bridging**:
   - When reaction resolution completes, inject bridging prompt to LLM: `"The narration was interrupted by [Player] casting [Spell]. Adjudicate the reaction and weave back into: [remaining_text]"`.

## Definition of Done
1. `the_watcher` consumes `VoiceSpeechInterrupted` events from Redis Streams and cancels in-flight LLM narration within 50ms.
2. Interrupted reaction intents bypass standard intent queuing and route to reaction resolution in < 200ms.
3. Remaining unread narration is archived in session chronicle without data loss.
