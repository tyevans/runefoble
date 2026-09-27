---
id: '0060'
title: Zero-Latency Neural Voice Duplex & Speech Interruption Handling
status: Accepted
created: 2026-09-26
persona: Marcus (The Casual Adventurer & Tactician)
feature: FEAT-VOX-06
governing_prd: PRD-0004
---

# US-0060 — Zero-Latency Neural Voice Duplex & Speech Interruption Handling

## Governing PRD
- [`PRD-0004: Dynamic Vocal Audio Conditioning and DSP Filters`](../../product/accepted/prd-0004-dynamic-vocal-audio-conditioning-and-dsp-filters.md)

## User Story

**As a** tabletop player conversing naturally with The Watcher AI Dungeon Master,  
**I want** to interrupt or speak over the AI DM without awkward waiting or delayed echo buffering,  
**So that** gameplay feels as dynamic, responsive, and spontaneous as a real-world table conversation.

## Scenario 1: Natural Human Speech Interruption (Barge-In)
```gherkin
Given The Watcher is narrating a 15-second atmospheric description of a goblin ambush
When Marcus abruptly interjects via microphone: "I cast Shield as an immediate reaction!"
Then the voice streaming pipeline detects the incoming speech within 80ms
And immediately halts the TTS audio playback stream with a 20ms soft crossfade
And routes Marcus's spoken reaction directly to the intent parser.
```

## Scenario 2: Acoustic Echo Cancellation & Cross-Talk Suppression
```gherkin
Given Marcus has loudspeaker audio enabled while speaking into his desktop microphone
When The Watcher delivers dialogue simultaneously with Marcus laughing or commenting
Then adaptive echo cancellation removes the speaker playback from the microphone capture buffer
Preventing false VAD triggers and speech-to-intent hallucination loops.
```
