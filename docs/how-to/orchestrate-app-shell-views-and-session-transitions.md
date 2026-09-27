# How to Orchestrate App Shell Views and Session Transitions

This how-to guide explains how the Runefoble App Shell (`frontend/src/runefoble-app.ts`) dynamically mounts routed microfrontend subviews, binds WebSocket connections strictly to active game sessions, and transitions participants from the pre-game assembly lobby to the live virtual tabletop.

## 1. App Shell Architecture & Route Mapping

The unified App Shell subscribes to the client SPA router (`Router`) and mounts the appropriate microfrontend based on the matched route pattern:

| Route Pattern | Active View | Mounted Microfrontend / Components |
|---|---|---|
| `#/login` / `#/register` | `login` | `<runefoble-auth-modal>` |
| `#/campaigns` | `campaigns` | `<runefoble-campaign-dashboard>` |
| `#/campaigns/:campaignId` | `campaign-detail` | `<runefoble-campaign-members>`, `<runefoble-session-list>` |
| `#/campaigns/:campaignId/characters` | `campaign-detail` | `<runefoble-campaign-members>`, `<runefoble-session-list>` |
| `#/characters` | `characters` | `<runefoble-character-roster>` |
| `#/campaigns/:campaignId/lobby/:sessionId` | `session-lobby` | `<runefoble-session-lobby>` |
| `#/campaigns/:campaignId/sessions/:sessionId` | `session-active` | `<runefoble-vtt-view>` (Tactical board, card, feed, voice) |

### View Resolution Example

```typescript
export function getActiveView(route: MatchedRoute | null): AppActiveView {
  const pat = route?.pattern || '';
  if (pat === '#/login' || pat === '#/register') return 'login';
  if (pat === '#/campaigns/:campaignId' || pat === '#/campaigns/:campaignId/characters') return 'campaign-detail';
  if (pat === '#/characters') return 'characters';
  if (pat === '#/campaigns/:campaignId/lobby/:sessionId') return 'session-lobby';
  if (pat === '#/campaigns/:campaignId/sessions/:sessionId') return 'session-active';
  return 'campaigns';
}
```

## 2. Route-Bound WebSocket Lifecycle Management

To prevent lingering connections, excessive memory usage, and background traffic, WebSocket connections are strictly scoped to session routes (`session-lobby` and `session-active`):

1. **Connection**: When entering a session route, `manageWebSocketLifecycle(route)` establishes a connection to `/ws/session/:sessionId`.
2. **Teardown**: When navigating to a non-session route (such as `#/campaigns` or `#/characters`), `disconnectWebSocket()` immediately closes the socket, removes event handlers, and cancels reconnect timers.
3. **Router Teardown**: The App Shell registers a router teardown hook via `router.registerTeardown()`, ensuring that any route transition out of a session cleanly shuts down the active socket.

```typescript
private manageWebSocketLifecycle(route: MatchedRoute) {
  const isSessionRoute = route.pattern === '#/campaigns/:campaignId/sessions/:sessionId' ||
                         route.pattern === '#/campaigns/:campaignId/lobby/:sessionId';
  if (isSessionRoute) {
    const targetSessionId = route.params.sessionId || this.sessionId;
    if (!this.socket || this.activeSocketSessionId !== targetSessionId) {
      this.connectWebSocket(targetSessionId);
    }
  } else {
    this.disconnectWebSocket();
  }
}
```

## 3. Session Start Transition (Lobby to Live VTT)

When a Dungeon Master starts the session or when an active session start broadcast is received:

1. **DM Launch**: The `<runefoble-session-lobby>` dispatches `@launch-session` with `{ campaignId, sessionId }`. The App Shell broadcasts `session_started` over the WebSocket and navigates the client router to `#/campaigns/:campaignId/sessions/:sessionId`.
2. **Participant Transition**: Connected players and spectators receive `{ type: 'session_started', campaignId, sessionId }` over the WebSocket. The App Shell router listener intercepts the message and automatically switches their view to the active tabletop session.

```typescript
private handleIncomingSocketMessage(msg: Record<string, any>) {
  if (msg.type === 'session_started') {
    const cId = msg.campaignId || this.campaignId;
    const sId = msg.sessionId || this.sessionId;
    router.navigate(`#/campaigns/${cId}/sessions/${sId}`);
  }
}
```

## 4. Route-Parameterized Service Fetching

Instead of hardcoded mock state, the App Shell fetches data parameterized by route attributes via `appDataService`:

- **Campaigns**: Fetches viewable campaigns from `GET /api/v1/campaigns`.
- **Campaign Detail**: Fetches roster from `GET /api/v1/campaigns/:id/members` and sessions from `GET /api/v1/campaigns/:id/sessions`.
- **Characters**: Fetches player characters from `GET /api/v1/characters`.
- **Session Lobby**: Fetches participant readiness from `GET /api/v1/sessions/:id`.
- **Active Tabletop**: Fetches tactical tokens from `GET /api/v1/boards/:id`.
