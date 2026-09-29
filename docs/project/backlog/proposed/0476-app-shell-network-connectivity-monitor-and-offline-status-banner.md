---
id: '0476'
title: App Shell Network Connectivity Monitor, Offline Status Banner, and Auto-Reconnection
status: Proposed
created: 2026-09-29
dependencies:
- TASK-0010
- TASK-0206
- TASK-0352
governing_adrs:
- ADR-0004
- ADR-0007
- ADR-0012
governing_prds:
- PRD-0005
- PRD-0023
governing_stories:
- US-0066
target_release: 0.9.0
---

# TASK-0476: App Shell Network Connectivity Monitor, Offline Status Banner, and Auto-Reconnection

## Status
Proposed

## Summary
Implement a browser-level network connectivity monitor and high-visibility offline status banner component (`<runefoble-network-status>`) in the App Shell, providing real-time online/offline detection, visual warning badges in `<runefoble-header>`, and automatic view data re-fetching upon network restoration.

## Problem Statement
In PRD-0023 Section 5, the App Shell navigation chrome requires a dynamic network connectivity badge and route-aware connectivity lifecycle. Currently, `runefoble-campaign-nav.ts` only reflects WebSocket connection status (`badge-socket`), which does not detect general browser network disruptions, offline mobile transitions, or HTTP gateway unreachability. When an adventurer experiences network packet loss or WiFi dropouts during long tabletop sessions, the UI continues displaying stale views without notifying the user that outbound mutations or chat messages cannot reach the server. Furthermore, when connection returns, the App Shell does not automatically reconcile view state or reconnect interrupted WebSockets.

## Governing Architecture & ADRs
- **ADR-0004: Lit Web Components and Storybook UI**: Encapsulated status component using design tokens.
- **ADR-0007: Real-Time Voice and Board Synchronization**: Automatic WebSocket reconnect and state re-sync upon network restoration.
- **ADR-0012: Design System Color Tokens and Contrast Invariants**: Accessible warning colors for degraded and offline states.

## Product & User Story References
- [`prd-0005-realtime-websocket-board-sync.md`](../../product/accepted/prd-0005-realtime-websocket-board-sync.md)
- [`prd-0023-unified-frontend-application-shell-and-campaign-hub.md`](../../product/accepted/prd-0023-unified-frontend-application-shell-and-campaign-hub.md)
- [`us-0066-client-side-routing-navigation-and-breadcrumbs.md`](../../user_stories/accepted/us-0066-client-side-routing-navigation-and-breadcrumbs.md)

## Scope of Work
1. **Network Status Service (`frontend/src/services/network-service.ts`)**:
   - Listen to window `'online'` and `'offline'` events with periodic heartbeat polling against `/healthz`.
   - Maintain reactive connection status: `'online'`, `'degraded'`, or `'offline'`.
   - Provide subscription callback API: `onStatusChange((status) => void)`.
2. **Network Status Banner & Header Badge (`frontend/src/components/runefoble-network-status.ts`)**:
   - Create Lit Web Component `<runefoble-network-status>` rendering a fixed top banner when offline or degraded with retry button.
   - Update `<runefoble-header>` to display a high-contrast connectivity pill badge (`● Online` / `○ Offline` / `▲ Reconnecting`).
   - Add Storybook stories in `frontend/src/stories/runefoble-network-status.stories.ts`.
3. **App Shell Reconnection Re-sync (`frontend/src/runefoble-app.ts`)**:
   - On transition from offline to online:
     - Trigger immediate reconnect on active session/lobby WebSocket if on live route.
     - Invoke `loadRouteData(currentRoute)` to re-fetch freshest campaign and character states.
     - Show temporary toast: "Connection restored — synchronized with server".

## Definition of Done
1. Network state transitions (online/offline) are tracked accurately across browser lifecycle.
2. An accessible, high-contrast offline banner renders across the App Shell whenever network connectivity is interrupted.
3. Restoring network connectivity triggers immediate WebSocket reconnection and data re-synchronization without requiring manual page reload.
4. Storybook stories cover online, degraded, and offline visual states.
5. All source files conform to Hard Invariant 6 (< 500 lines per file).
