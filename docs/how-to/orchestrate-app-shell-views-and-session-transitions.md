# How to Orchestrate App Shell Views and Session Transitions

This how-to guide explains how the Runefoble App Shell (`frontend/src/runefoble-app.ts`) dynamically mounts routed microfrontend subviews, binds WebSocket connections strictly to active game sessions, and transitions participants from the pre-game assembly lobby to the live virtual tabletop.

## 1. App Shell Architecture & Route Mapping

The unified App Shell subscribes to the client SPA router (`Router`) and mounts the appropriate microfrontend based on the matched route pattern:

| Route Pattern | Active View | Mounted Microfrontend / Components |
|---|---|---|
| `#/login` / `#/register` | `login` | `<runefoble-auth-modal>` |
| `#/campaigns` | `campaigns` | `<runefoble-campaign-dashboard>` |
| `#/campaigns/:campaignId` | `campaign-detail` | `<runefoble-campaign-header>`, tab navigation bar (`Overview & Sessions`, `Party Characters`, `Codex & Lore`, `Chronicle & Stats`), `<runefoble-campaign-members>`, `<runefoble-session-list>` |
| `#/campaigns/:campaignId/characters` | `campaign-characters` | `<runefoble-campaign-header>`, tab navigation bar, `<runefoble-character-roster>` (scoped to campaign) |
| `#/characters` | `characters` | `<runefoble-character-roster>` |
| `#/characters/:characterId` | `character-sheet` | `<runefoble-character-sheet>`, `<runefoble-stand-in-guardrails>` |
| `#/profile` | `profile` | `<runefoble-user-profile>` (User claims, role badges, theme selection) |
| `#/campaigns/:campaignId/lobby/:sessionId` | `session-lobby` | `<runefoble-session-lobby>` |
| `#/campaigns/:campaignId/sessions/:sessionId` | `session-active` | `<runefoble-vtt-view>` (Tactical board, card, feed, voice) |

### View Resolution Example

```typescript
export function getActiveView(route: MatchedRoute | null): AppActiveView {
  const pat = route?.pattern || '';
  if (pat === '#/login' || pat === '#/register') return 'login';
  if (pat.startsWith('#/campaigns/:campaignId/lobby/')) return 'session-lobby';
  if (pat.startsWith('#/campaigns/:campaignId/sessions/')) return 'session-active';
  if (pat === '#/campaigns/:campaignId/characters') return 'campaign-characters';
  if (pat.startsWith('#/campaigns/:campaignId')) return 'campaign-detail';
  if (pat.startsWith('#/characters/') && pat !== '#/characters') return 'character-sheet';
  if (pat === '#/characters') return 'characters';
  return pat === '#/profile' ? 'profile' : 'campaigns';
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
- **Campaign Metadata & Updates**: Fetches metadata from `GET /api/v1/campaigns/:id` and persists updates from `@update-campaign` via `PATCH /api/v1/campaigns/:id` with Zanzibar authorization.
- **Campaign Detail**: Fetches roster from `GET /api/v1/campaigns/:id/members` and sessions from `GET /api/v1/campaigns/:id/sessions`.
- **Characters**: Fetches player characters from `GET /api/v1/characters` and scopes party roster in `#/campaigns/:id/characters`.
- **Session Lobby**: Fetches participant readiness from `GET /api/v1/sessions/:id`.
- **Active Tabletop**: Fetches tactical tokens from `GET /api/v1/boards/:id`.
- **Session Scheduling & Staging**: Creates new sessions or launches staging lobbies from `POST /api/v1/campaigns/:id/sessions` via `<runefoble-session-modal>`.

## 5. Character Roster Event Binding & Data Mutations

When mounting `<runefoble-character-roster>` on the `#/characters` route, the App Shell wires event listeners for all dispatched roster actions to bridge UI interactions with Gateway API persistence:

| Event | Dispatched Detail | App Shell Handler | Gateway Endpoint / State Mutation |
|---|---|---|---|
| `@create-character` | `CreateCharacterPayload` | `handleCreateCharacter(e)` | `POST /api/v1/characters` via `appDataService.createCharacter()` + toast confirmation + roster refresh |
| `@assign-campaign` | `AssignCampaignEventDetail` | `handleAssignCampaign(e)` | `PATCH /api/v1/characters/:id/campaign` via `appDataService.assignCharacterCampaign()` + local tag update |
| `@delete-character` | `DeleteCharacterEventDetail` | `handleDeleteCharacter(e)` | `DELETE /api/v1/characters/:id` via `appDataService.deleteCharacter()` + roster removal |
| `@inspect-character` | `InspectCharacterEventDetail` | `handleInspectCharacter(e)` | Navigates router to `#/characters/:characterId` via `router.navigate()` |

```typescript
if (v === 'characters') {
  return html`
    <runefoble-character-roster
      .characters=${this.characters}
      .campaigns=${this.rosterCampaigns}
      current-user-id=${this.currentUserId}
      @create-character=${this.handleCreateCharacter}
      @assign-campaign=${this.handleAssignCampaign}
      @delete-character=${this.handleDeleteCharacter}
      @inspect-character=${this.handleInspectCharacter}
    ></runefoble-character-roster>
  `;
}
```

## 6. Auditing View Wiring and Regression Verification

To prevent view collisions (such as `#/profile` defaulting to `campaigns` or `#/campaigns/:id/characters` colliding with `campaign-detail`) and verify route-bound WebSocket lifecycles:

- **Frontend Component & Route Matrix**: Run `node --experimental-strip-types --test frontend/test/app-shell-views-wiring-audit.test.ts` to execute parameterized assertions across all standard routes, verifying parameter extraction, breadcrumbs, and WebSocket connect/teardown events.
- **Python E2E Blackbox Suite**: Run `pytest tests/test_blackbox_app_shell_views_audit.py` to audit full frontdoor Gateway API endpoints, DOM mounting manifest contracts, and file length constraints.

