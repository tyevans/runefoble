# How to Orchestrate App Shell Views and Session Transitions

This how-to guide explains how the Runefoble App Shell (`frontend/src/runefoble-app.ts`) dynamically mounts routed microfrontend subviews, binds WebSocket connections strictly to active game sessions, and transitions participants from the pre-game assembly lobby to the live virtual tabletop.

## Source Layout

`frontend/src/runefoble-app.ts` owns the Lit element, the route wiring, and the public handler methods. It delegates the work to modules in `frontend/src/app/`. Each module has one responsibility.

| Module | Responsibility |
|---|---|
| `app/component-registry.ts` | Loads the shell chrome elements at startup. `loadViewBundles(view)` loads each microfrontend bundle by route with a dynamic `import()`. |
| `router/view-resolver.ts` | Pure map from a matched route to a view id. The app and the view tests both import `resolveActiveView`. |
| `app/route-state.ts` | Copies a matched route into the shell state: params, breadcrumbs, and campaign and session titles. |
| `app/shell-state.ts` | Applies the stored theme. Syncs the user role to the shell. Stores the campaign capability flags and registers the DM-only plugins. |
| `app/shell-template.ts` | Renders the header, the main region, the toast, the modals, and the absentee overlays. |
| `views/index.ts` | `VIEW_CONTROLLERS`: one controller per view id. A controller renders its view and loads its data. |
| `views/campaign-dashboard-view.ts`, `campaign-hub-view.ts`, `lobby-view.ts`, `session-view.ts`, `character-view.ts`, `profile-view.ts` | The route view controllers. Each one owns the template and the data read for its route. |
| `app/absentee-overlays.ts` | Renders the absentee stance drawer. |
| `app/data-loader.ts` | Runs the campaign switcher read and the view controller read. A failed read sets `loadError`. |
| `app/session-data-loader.ts` | Loads lobby and active-session data. |
| `app/session-socket.ts` | Opens, closes, and reconnects the session WebSocket. A failed open or message logs the error and shows a toast. |
| `app/session-actions.ts` | Handles the launch-session and stand-in toggle events. |
| `app/session-messages.ts` | Applies live session messages to shell state. |
| `app/campaign-actions.ts` | Handles campaign, session, membership, and invite events. |
| `app/character-actions.ts` | Handles roster and lobby character events. |
| `app/title-resolver.ts` | Resolves breadcrumb titles. |
| `app/load-error.ts` | Stores the first failed read as the load error. |

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
| `#/rules` | `rules` | `<runefoble-rules-compendium>` (SRD search and encounter builder tabs; no homebrew tab without a campaign). The view passes the gateway origin as `apiBaseUrl`. |
| `#/campaigns/:campaignId/rules` | `campaign-rules` | `<runefoble-rules-compendium>` with `campaignId` (adds the homebrew forge tab). Mounted by the campaign hub as the Rules tab. |
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
   The gateway refuses a user who lacks `session.observe` on that session. It closes the socket with code 4403. A message reaches only the sockets of its own session. One gateway replica holds these groups. With several replicas, a client sees only the messages that its own replica handled.
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

The App Shell fetches data parameterized by route attributes via `appDataService`. Each call returns a `DataResult`. A failed read sets `loadError`, which renders `<runefoble-data-error>`. The App Shell never substitutes fixture data:

- **Campaigns**: Fetches viewable campaigns from `GET /api/v1/campaigns`.
- **Campaign Metadata & Updates**: Fetches metadata from `GET /api/v1/campaigns/:id` and persists updates from `@update-campaign` via `PATCH /api/v1/campaigns/:id` with Zanzibar authorization.
- **Campaign Detail**: Fetches roster from `GET /api/v1/campaigns/:id/members` and sessions from `GET /api/v1/campaigns/:id/sessions`.
- **Characters**: Fetches player characters from `GET /api/v1/characters` and scopes party roster in `#/campaigns/:id/characters`.
- **Session Lobby**: Fetches participant readiness from `GET /api/v1/sessions/:id`.
- **Active Tabletop**: Fetches tactical tokens from `GET /api/v1/boards/:id`. The route returns `404` for an unknown board and never creates one. Create the board first with `POST /api/v1/boards`.
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

## 6. Dynamic Character Binding in Lobby and Active VTT (TASK-0256)

During session staging and active virtual tabletop play, the App Shell dynamically resolves and binds the player's active character:

1. **Lobby Roster Population**: `appDataService.fetchLobbyState(campaignId, sessionId)` queries the user's real character roster and prioritizes characters assigned to the active campaign.
2. **Lobby Selection Sync**: When a player selects a character in `<runefoble-session-lobby>`, the component emits `@select-character` (and `@character-selected`), storing the selection in App Shell `activeCharacter` state and updating participant cards.
3. **Session Transition & Character Resolution**: When launching or entering `session-active` (`#/campaigns/:id/sessions/:sessionId`), `resolveActiveCharacter(campaignId)` preserves any character chosen during lobby staging. If no selection was made, it selects:
   - The first character assigned to the specified `campaignId`.
   - The user's first available character in their roster.
   - When the roster is empty, `resolveActiveCharacter` returns `null`. The session view shows an empty state that asks the user to choose a character in the lobby. No placeholder character is created (TASK-0642).
4. **VTT Character Card Binding**: The `<runefoble-character-card>` dynamically receives `.characterName`, `.characterClass`, `.level`, `.currentHp`, `.maxHp`, `.armorClass`, and `.portraitUrl`.
5. **DM Party Inspector & Switcher**: When the campaign capabilities report `run_session`, a high-contrast inspection banner and `<select class="dm-character-switcher">` allow the Dungeon Master to inspect and switch active character cards across the entire party.

## 7. Auditing View Wiring and Regression Verification

To prevent view collisions (such as `#/profile` defaulting to `campaigns` or `#/campaigns/:id/characters` colliding with `campaign-detail`) and verify route-bound WebSocket lifecycles:

- **Frontend Component & Route Matrix**: Run `node --experimental-strip-types --test frontend/test/app-shell-views-wiring-audit.test.ts` to execute parameterized assertions across all standard routes, verifying parameter extraction, breadcrumbs, and WebSocket connect/teardown events.
- **Modular App Shell Test Submodules**: Run `node --experimental-strip-types --test frontend/test/app_shell/*.test.ts` (or `npm test` in `frontend/`) to execute the decomposed unit and integration test submodules (`routing.test.ts`, `session-transitions.test.ts`, `websocket-lifecycle.test.ts`, `state-breadcrumbs.test.ts`).
- **Python E2E Blackbox Suite**: Run `pytest tests/test_blackbox_app_shell_views_audit.py` and `pytest tests/test_blackbox_app_shell_test_modular_decomposition.py` to audit full frontdoor Gateway API endpoints, DOM mounting manifest contracts, file length constraints, and modular test execution.

## 8. Live Tabletop VTT WebSocket Event Mesh & Plugin Slots (TASK-0358)

In the active session (`session-active`) and pre-game lobby (`session-lobby`), the App Shell binds multi-user real-time events over `/ws/session/:sessionId`:

1. **Session Lobby Readiness & Absentee AI Stand-In Sync**:
   - `<runefoble-session-lobby>` dispatches `@toggle-readiness` and `@toggle-stand-in`.
   - The App Shell updates `lobbyParticipants` state and broadcasts `{ type: 'player_readiness', userId, isReady }` and `{ type: 'player_stand_in', userId, isAbsent }` to all connected party members.
2. **Tactical Board Event Mesh & Dynamic Bounds**:
   - `<runefoble-board>` receives `.cols` and `.rows` dynamically from `appDataService.fetchBoardState(sessionId)` and `.websocketUrl` connecting directly to the session WebSocket.
   - Listens to board actions:
     - `@token-action`: Broadcasts `{ type: 'token_action', ... }` (radial menu actions).
     - `@aoe-place`: Broadcasts `{ type: 'aoe_placed', ... }` (geometric spell placements).
     - `@spell-vfx-triggered`: Broadcasts `{ type: 'spell_vfx', ... }` (WebGL particle bloom).
     - `@confirm-ghost`: Broadcasts `{ type: 'confirm_ghost', ... }` (spoken movement finalization).
3. **Default Tabletop Plugin Seeding**:
   - `pluginRegistry` is seeded via `registerDefaultPlugins(registry, canRunSession)`. `setCampaignCapabilities()` calls it with the `run_session` flag (TASK-0559):
     - Slot `hud-widget`: `<runefoble-initiative-tracker>`, `<runefoble-soundscape-controls>`.
     - Slot `dice-panel`: `<runefoble-dice-roller>`, `<runefoble-dice-tray-3d>`.
     - Slot `sidebar-tool`: `<runefoble-combat-reaction-prompt>`, plus `<runefoble-dm-whisper-bar>` and `<runefoble-dm-trap-controls>` when `run_session` is true.
4. **Expanded WebSocket Message Routing**: The App Shell does not query service elements. It dispatches each message as a window event (`frontend/src/vtt-mesh-handlers.ts`). The owning element subscribes to the event. The event names and payloads are in [`microfrontend-architecture.md`](../reference/microfrontend-architecture.md#session-mesh-events).
   - `dice_rolled` (`runefoble:dice-rolled`): `<runefoble-dice-tray-3d>` tosses the dice. `<runefoble-dice-roller>` shows the forced result. `<runefoble-board>` runs the 3D roll.
   - `turn_advanced` (`runefoble:turn-advanced`): `<runefoble-initiative-tracker>` moves the active combatant and round. `<runefoble-board>` marks the active turn token.
   - `aoe_placed` (`runefoble:aoe-placed`): `<runefoble-board>` renders the AoE spell template.
   - `spell_vfx` (`runefoble:spell-vfx`): `<runefoble-board>` triggers the WebGL particle bloom.
   - `dm_whisper` (`runefoble:dm-whisper`): `<runefoble-dm-whisper-bar>` adds the private DM whisper.

## 9. Capability-Gated Views (TASK-0559)

The App Shell does not read role strings. Each loader that opens a campaign reads `GET /api/v1/campaigns/{campaign_id}/capabilities` in the same request batch as the campaign. The gateway returns one boolean per `campaign` permission in `runefoble.zed`:

| Flag | Gates |
|---|---|
| `manage` | Campaign settings, members, and the Asset Forge tab (`resolveForgeAccess`) |
| `run_session` | Session creation and launch, DM Party Inspector, DM-only plugins, and the DM secret codex and atlas |
| `play` | Player-level campaign actions |
| `view` | Read access to the campaign |

The flags only shape the view. The service checks stay authoritative. A missing or failed capability read sets `loadError`. It never grants a flag. When the open campaign changes, the flags reset until the loader sets the new ones.
