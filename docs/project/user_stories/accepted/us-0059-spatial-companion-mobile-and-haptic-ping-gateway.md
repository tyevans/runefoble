---
id: '0059'
title: Spatial Companion Mobile WebRTC Audio & Haptic Secret Pings
status: Accepted
created: 2026-09-26
persona: Marcus (The Casual Adventurer & Tactician)
feature: FEAT-VOX-01
governing_prd: PRD-0004
---

# US-0059 — Spatial Companion Mobile WebRTC Audio & Haptic Secret Pings

## Governing PRD
- [`PRD-0004: Dynamic Vocal Audio Conditioning and DSP Filters`](../../product/accepted/prd-0004-dynamic-vocal-audio-conditioning-and-dsp-filters.md)

## User Story

**As a** player participating in tabletop sessions via mobile phone or tablet,  
**I want** a dedicated low-bandwidth WebRTC companion endpoint with haptic vibration alerts for secret DM whispers and roll turns,  
**So that** I can stay fully immersed and react to private messages even when away from my primary desktop display.

## Scenario 1: Haptic Secret DM Whisper Alert
```gherkin
Given Marcus is connected via his mobile phone companion app
When The Watcher or human DM sends a secret narrative whisper ("You feel cold breath upon the back of your neck")
Then Marcus's phone delivers a distinct triple-pulse haptic vibration
And displays the diegetic whisper on the lockscreen/app overlay without revealing the message to other players.
```

## Scenario 2: Low-Bandwidth Adaptive Audio Streaming
```gherkin
Given Marcus moves into an area with constrained cellular data bandwidth (< 50 kbps)
When active WebRTC audio packets begin dropping
Then the gateway automatically adapts down to Opus voice-optimized mono 16kHz stream
Preserving voice clarity and push-to-talk responsiveness without disconnects.
```
