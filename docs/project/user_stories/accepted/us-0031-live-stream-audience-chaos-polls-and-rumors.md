---
id: 0031
title: Live Stream Audience Chaos Polls via TypeScript Backend
status: Shipped
created: 2026-09-25
governing_prd: PRD-0011
---

# US-0031 — Live Stream Audience Chaos Polls via TypeScript Backend

## Governing PRD
- [`PRD-0011: Live Spectator Studio & Two-Way Audience Interactivity`](../../product/accepted/prd-0011-live-spectator-studio-and-audience-interactivity.md)

## User Story

**As a** streamer cultivating an engaged online community (Devon),  
**I want** stream viewers to vote on minor twists handled by a dedicated TypeScript backend service,  
**So that** high-concurrency Twitch/YouTube chat events process in real-time without slowing game servers.

## Acceptance Criteria

1. **TypeScript Backend Concurrency**: The `audience_studio` TypeScript service handles chat events, WebSocket fanout, and Twitch/YouTube voting.
2. **Audience Chaos Polls**: Live viewers vote on minor encounter twists (e.g. weather shifts, minor blessings).
3. **DM Approval Gate**: Winning audience poll outcomes require DM confirmation before mechanical effects apply to `game_session`.
