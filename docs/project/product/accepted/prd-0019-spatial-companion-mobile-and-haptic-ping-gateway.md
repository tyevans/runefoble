---
id: '0019'
title: Spatial Companion Mobile Experience, Low-Bandwidth WebRTC & Haptic Secret Pings
status: Accepted
created: 2026-09-26
---

# PRD-0019 — Spatial Companion Mobile Experience, Low-Bandwidth WebRTC & Haptic Secret Pings

## Who this is for

Casual adventurers (like Marcus) who prefer relaxing on the couch without a bulky laptop, absent or traveling players (like Sarah) who need a pocket window into game night, and Game Masters (like Evelyn) delivering secret diegetic communications.

## What the person cannot do today

- Existing virtual tabletops require a full desktop web browser and multi-monitor setup, chaining players to a computer desk and excluding comfortable living room or mobile play.
- Mobile participants on cellular data suffer constant audio stuttering, dropped WebRTC packets, and excessive bandwidth consumption.
- Secret DM whispers (e.g. passive perception alerts, hidden curse effects, clandestine notes) pop up in text boxes that can be inadvertently seen by roommates or stream viewers, lacking physical intimacy.
- Absent players who must step away or commute have no lightweight mobile interface to inspect their AI stand-in's status, adjust tactical boundaries, or listen to session highlights.

## What good looks like

1. **Lightweight Mobile Companion Web Application**:
   - Touch-optimized progressive web app (PWA) displaying active turn indicators, character vitals, quick-action dice roller, and push-to-talk microphone.
   - Low CPU and battery footprint allowing full 4-hour session participation on mobile devices without overheating.
2. **Private Physical Haptic Secret Pings**:
   - Distinct smartphone vibration patterns providing tactile physical feedback without visual screen leakage:
     - Single sharp pulse: Player's turn in initiative order.
     - Rhythmic double pulse: Private party chat or trade request.
     - Urgent triple pulse: Secret DM whisper or danger perception trigger.
   - Lockscreen and notification overlay presenting private text whispers discreetly.
3. **Adaptive Low-Bandwidth Opus WebRTC Gateway**:
   - Smart audio streaming client that automatically adapts to fluctuating network conditions, scaling down to an ultra-efficient 16kHz mono Opus stream (<50 kbps) when cellular signal weakens.
   - High-packet-loss concealment preventing jarring audio dropouts during transit.
4. **Absentee Mobile Session Portal**:
   - Sarah can check in from her phone during a work break to view her character's current HP, consumed spell slots, and standing stance (Defensive, Cautious, Heroic).
   - Instant access to a generated 2-minute audio recap reel detailing stand-in actions and hilarious penalty moments upon returning.

## What this does not do

- It does not attempt to render full 3D WebGL tactical battlemaps on low-power mobile devices; it focuses purely on the audio, haptic, character sheet, and decision stream.
- It does not expose private whisper notifications to desktop spectator overlays or streaming broadcasts.

## Checkable Outcomes

1. Companion mobile WebRTC audio connects within 300ms and sustains clear voice communication on simulated 50 kbps constrained connections.
2. Haptic vibration pulses execute within 50ms of incoming secret DM events via the standard Web Vibration API.
3. Mobile PWA achieves 60fps scrolling and touch responsiveness on modern iOS and Android mobile browsers.
4. Absentee character status queries and tactical directive updates resolve over HTTP/WebSocket in under 100ms.

## Linked User Stories
- [`US-0059: Spatial Companion Mobile WebRTC Audio & Haptic Secret Pings`](../../user_stories/accepted/us-0059-spatial-companion-mobile-and-haptic-ping-gateway.md)
- [`US-0027: Absentee Character Resource Ledger & Recap Reel`](../../user_stories/accepted/us-0027-absentee-character-resource-ledger-and-recap-reel.md)

## Implementing Backlog Tasks
- [`TASK-0128: Spatial Companion Mobile & Haptic Gateway`](../../backlog/complete/0128-spatial-companion-mobile-and-haptic-gateway.md)
- [`TASK-0134: Spatial Companion Mobile Audio & Haptic Microfrontend`](../../backlog/complete/0134-spatial-companion-mobile-audio-and-haptic-microfrontend.md)
- [`TASK-0166: Mobile Low-Bandwidth Opus Adaptive Stream Adapter`](../../backlog/refined/0166-mobile-low-bandwidth-opus-stream-adapter.md)
- [`TASK-0167: Absentee Mobile Directive and Remote Voting Microfrontend`](../../backlog/refined/0167-absentee-mobile-directive-voting-microfrontend.md)
