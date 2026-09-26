---
id: 0031
title: Live Stream Audience Chaos Polls via TypeScript Backend
status: Accepted
created: 2026-09-25
---

# US-0031 — Live Stream Audience Chaos Polls via TypeScript Backend

## User Story

**As a** streamer cultivating an engaged online community (Devon),  
**I want** stream viewers to vote on minor twists handled by a dedicated TypeScript backend service,  
**So that** high-concurrency Twitch/YouTube chat events process in real-time without slowing game servers.

## Acceptance Criteria

1. **TypeScript Backend Concurrency**: The `audience_studio` TypeScript service handles chat events, WebSocket fanout, and Twitch/YouTube voting.
2. **Audience Chaos Polls**: Live viewers vote on minor encounter twists (e.g. weather shifts, minor blessings).
3. **DM Approval Gate**: Winning audience poll outcomes require DM confirmation before mechanical effects apply to `game_session`.
