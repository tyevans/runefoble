---
id: '0020'
title: Zero-Latency Neural Voice Duplex, Barge-In Interruption & Acoustic Echo Cancellation
status: Accepted
created: 2026-09-26
---

# PRD-0020 — Zero-Latency Neural Voice Duplex, Barge-In Interruption & Acoustic Echo Cancellation

## Who this is for

Voice-first tabletop roleplayers (like Marcus), expressive dramatic performers (like Nadia), and Game Masters (like Evelyn) who want AI-driven tabletop conversations to feel like lively, spontaneous, real-world table talk without robotic turn-taking delays.

## What the person cannot do today

- Voice interactions with AI assistants feel rigid and robotic: players must wait politely until the AI finishes its entire spoken response before speaking.
- In high-stakes combat, players cannot interrupt the AI DM to call out instantaneous reactions (e.g. "I cast Shield!" or "I use my Sentinel attack!"), resulting in desynchronized turns.
- Using desktop speakers causes AI DM speech to bleed into the player's microphone, triggering false voice activity detection (VAD), speech feedback loops, and intent parsing errors.
- Push-to-talk keys break physical immersion and conversational theater, while open microphones frequently suffer from accidental background noise cutoffs.

## What good looks like

1. **Sub-80ms Speech Barge-In Detection**:
   - Neural voice activity detection (VAD) continuously monitoring incoming audio streams during AI speech playback.
   - When a human speaker begins vocalizing, incoming speech onset is detected within 80ms, immediately halting AI TTS playback with an imperceptible 20ms soft crossfade.
2. **Hardware-Accelerated Acoustic Echo Cancellation (AEC)**:
   - Real-time adaptive filtering that subtracts speaker audio output from the microphone capture buffer, allowing open-mic tabletop play through room loudspeakers without headphones.
   - Robust cross-talk suppression separating player laughter and commentary from legitimate gameplay commands.
3. **Conversational Intent Prioritization & Reactive Routing**:
   - Interrupted utterances are immediately classified into priority intent tiers: emergency reactions (Shield, Counterspell), tactical interruptions, or social commentary.
   - The Watcher pauses scene narration, adjudicates the player's immediate reaction, and seamlessly resumes or adapts the narrative flow.
4. **Voice Duplex Audio Settings & Energy Visualizer**:
   - Intuitive settings panel displaying real-time microphone input energy, interruption sensitivity slider, background noise threshold, and AEC status.

## What this does not do

- It does not cut off AI DM speech on non-verbal transient noises such as throat clearing, coughing, chair squeaks, or passing sirens.
- It does not lose the transcript context of aborted narration; unread text remains archived in the session chronicle log.

## Checkable Outcomes

1. Speech barge-in detection halts active TTS audio output within 100ms of human speech onset across square/sine test benchmarks.
2. Acoustic echo cancellation delivers >35dB echo return loss enhancement (ERLE) on loudspeaker setups with zero intent hallucinations.
3. Interrupted reaction intents (e.g. Counterspell / Shield) route to the rules adjudication engine in under 200ms.
4. Microfrontend voice duplex settings panel renders real-time audio levels and barge-in visualizer maintaining 60fps rendering.

## Linked User Stories
- [`US-0060: Zero-Latency Neural Voice Duplex & Speech Interruption Handling`](../../user_stories/accepted/us-0060-zero-latency-neural-voice-duplex.md)
- [`US-0023: Spoken Reaction Interrupts and Ready Actions`](../../user_stories/accepted/us-0023-spoken-reaction-interrupts-and-ready-actions.md)

## Implementing Backlog Tasks
- [`TASK-0141: Zero-Latency Neural Voice Duplex & Speech Interruption Handling`](../../backlog/complete/0141-zero-latency-neural-voice-duplex-and-interruption.md)
- [`TASK-0149: Voice Duplex Audio Settings & Real-Time Barge-In Visualizer Microfrontend`](../../backlog/complete/0149-voice-duplex-barge-in-visualizer-microfrontend.md)
- [`TASK-0168: Neural Speech Barge-In and Soft Crossfade Audio Filter`](../../backlog/proposed/0168-neural-speech-barge-in-crossfade-filter.md)
- [`TASK-0169: Hardware Acoustic Echo Cancellation and ERLE Validation`](../../backlog/proposed/0169-hardware-aec-filter-and-erle-validation.md)
