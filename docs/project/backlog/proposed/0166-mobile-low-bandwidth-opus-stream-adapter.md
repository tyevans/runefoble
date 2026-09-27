---
id: '0166'
title: Mobile Low-Bandwidth Opus Adaptive Stream Adapter
status: Proposed
created: 2026-09-26
dependencies:
- TASK-0128
governing_adrs:
- ADR-0002
- ADR-0003
governing_prds:
- PRD-0019
governing_stories:
- US-0059
target_release: 0.7.0
---

# TASK-0166: Mobile Low-Bandwidth Opus Adaptive Stream Adapter

## Status
Proposed

## Summary
Implement network-adaptive WebRTC stream bitrate scaling in `services/voice_agent/`, automatically stepping audio transmission down to 16kHz mono Opus (<50 kbps) when mobile participants experience packet loss.

## Problem Statement
Players connecting via mobile cellular networks suffer severe audio stuttering and disconnections during high-latency or packet-constrained intervals when high-definition stereo streams are mandated.

## Governing Architecture & ADRs
- **ADR-0002: Event-Driven Watcher Gameplay Orchestration**: Real-time audio routing.
- **ADR-0003: UV Monorepo Workspace for Python BCs**: Clean module layout in `voice_agent`.

## Scope of Work
1. **Network Quality Metric Monitor**:
   - WebRTC RTCP receiver report analyzer detecting packet loss (>5%) and round-trip delay spikes.
2. **Adaptive Bitrate Step-Down Regulator**:
   - Dynamic Opus codec parameter adjustment reducing complexity and bitrate while preserving voice intelligibility.
3. **Frontdoor Verification**:
   - Synthetic network degradation tests asserting uninterrupted audio streaming under 50 kbps caps.

## Definition of Done
- Adapter implemented in `services/voice_agent/src/voice_agent/`.
- Bitrate transitions trigger within 200ms of packet loss detection.
- Unit tests verify codec reconfiguration without socket dropouts.
- File length remains under 250 lines.
