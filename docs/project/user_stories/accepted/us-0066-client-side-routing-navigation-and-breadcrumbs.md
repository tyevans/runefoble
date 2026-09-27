---
id: 0066
title: Application Shell Client-Side Routing, Navigation Chrome, and Route Lifecycle
status: Accepted
created: 2026-09-27
persona: Devon (The Live Streamer / Spectator) & Marcus (The Voice-First Casual Adventurer)
feature: FEAT-UI-11
governing_prd: PRD-0023
---

# US-0066 — Application Shell Client-Side Routing, Navigation Chrome, and Route Lifecycle

## Governing PRD
- [`PRD-0023: Unified Frontend Experience with User Authentication, Campaign Hub, and Session Orchestration`](../../product/accepted/prd-0023-unified-frontend-application-shell-and-campaign-hub.md)

## User Story

**As a** tabletop player, DM, or spectator,
**I want** responsive client-side routing with deep-linkable URLs, dynamic breadcrumbs, and route-aware WebSocket lifecycle management,
**So that** I can share direct links to campaigns, lobbies, or live spectator streams, navigate cleanly back and forth with browser history, and never leak background WebSocket connections across views.

## Scenario 1: Deep-Linking to a Session View
```gherkin
Given a user clicks a shared link "http://localhost/#/campaigns/4/sessions/14"
When the application loads
Then the client router matches the route parameters "campaignId=4" and "sessionId=14"
And the App Shell mounts the active VTT view
And the navigation bar renders breadcrumbs "Campaigns > Tomb of the Star-Eater > Session #14"
And the session WebSocket connects specifically for session "14".
```

## Scenario 2: Route Teardown and Cleanup
```gherkin
Given a user is in an active session at "#/campaigns/4/sessions/14" with an active WebSocket
When the user clicks the "Campaigns" breadcrumb to navigate to "#/campaigns"
Then the active session WebSocket is cleanly closed
And audio streams and board animation animation frames are halted
And the Campaign Dashboard view mounts without memory leaks or stale socket listeners.
```
