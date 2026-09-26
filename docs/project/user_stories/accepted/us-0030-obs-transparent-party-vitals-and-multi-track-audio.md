---
id: 0030
title: OBS Transparent Party Vitals Overlay and Multi-Track Audio Output
status: Accepted
created: 2026-09-25
governing_prd: PRD-0011
---

# US-0030 — OBS Transparent Party Vitals Overlay and Multi-Track Audio Output

## Governing PRD
- [`PRD-0011: Live Spectator Studio & Two-Way Audience Interactivity`](../../product/accepted/prd-0011-live-spectator-studio-and-audience-interactivity.md)

## User Story

**As a** streamer managing audio levels and video overlays in OBS (Devon),  
**I want to** embed a transparent party vitals widget and route Watcher dialogue over isolated audio tracks,  
**So that** my stream display is broadcast-ready and my audio mix is crystal clear.

## Acceptance Criteria

1. **Transparent Stream Overlay**: Provides a dedicated browser-source URL displaying animated party HP bars, conditions, and active speaker badges with transparent alpha-channel background.
2. **Multi-Track Audio Routing**: Isolates Watcher DM narration, character speech synthesis, and background music onto distinct virtual audio stems or channels.
3. **Low Overhead**: The stream overlay maintains sub-16ms render frames without consuming excessive CPU/GPU resources on the streaming machine.
