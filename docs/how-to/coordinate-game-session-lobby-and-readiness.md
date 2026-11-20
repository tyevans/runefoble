# How to Coordinate Game Session Lobby, Participant Readiness, and Live Launch

This guide demonstrates how to stage pre-game assembly with `<runefoble-session-lobby>`, coordinate participant readiness and absentee AI stand-ins, and orchestrate live tabletop session launches governed by SpiceDB Zanzibar object authorization.

## Prerequisites

- Local development environment or Kind cluster running (`uv run pytest` or `make cluster-up`).
- Authenticated user session with Zitadel JWT bearer token.
- Running `game_session` and `character_sheet` services.

---

## 1. Overview & Architecture

Before entering active tactical combat or exploration, players and Game Masters gather in the session staging lobby (`#/campaigns/:campaignId/lobby/:sessionId`). The lobby fulfills three critical coordination requirements:
1. **Attendance & Presence Verification**: Shows real-time presence (online, idle, offline) for all invited party members.
2. **Character Lock-in & Readiness**: Allows players to select from their owned characters and toggle readiness ("Ready" vs. "Setting Up").
3. **AI Stand-In & Launch Orchestration**: Allows marking absent players for AI stand-in takeover and provides the Game Master with a one-click session launch triggering `POST /api/v1/sessions/:id/start`.

---

## 2. Using `<runefoble-session-lobby>` Component

The `<runefoble-session-lobby>` component is vendored in `@runefoble/game-session-ui` and conforms to ADR-0004, ADR-0012, and ADR-0013.

### Component Attributes & Properties

| Attribute / Property | Type | Description |
|---|---|---|
| `session-id` | `string` | Unique session identifier UUID |
| `campaign-id` | `string` | Owning campaign identifier |
| `session-title` | `string` | Display title for the game session |
| `current-user-id` | `string` | User ID of the logged-in participant |
| `participants` (property) | `LobbyParticipant[]` | Array of participant objects with readiness state |
| `availableCharacters` (property) | `LobbyCharacterOption[]` | List of owned characters available for selection |
| `is-dm` | `boolean` | The caller holds `campaign.run_session` (server capability reply). Shows the Launch Session control and hides Take a Seat |
| `can-play` | `boolean` | The caller holds `campaign.play` (server capability reply). With `is-dm` false and no seat for `current-user-id`, the lobby shows Take a Seat (TASK-0889) |
| `is-loading` | `boolean` | Loading indicator disabling interactive triggers |

### Readiness Summary

The readiness pill counts players only. A participant with the `owner` role or a DM role (`dm` or `dungeon_master`) coordinates the session. The lobby never counts that participant as a player. A spectator is never counted. The lobby reads role strings through one normalizer, `services/game_session/ui/src/lobby/roles.ts`.

| Participants present | Pill text |
|---|---|
| Only a DM, or only an owner and spectators | `No players have joined` |
| Two players, one ready | `1 of 2 players ready` |
| Two players, one ready, one absent stand-in | `1 of 2 players ready, 1 absent stand-in` |

With no player present, the summary has no fallback count. The pill never counts a DM as a ready player.

### Launch Rule (TASK-0952)

Readiness never blocks the launch. The DM can launch the session at any time from the lobby. A seat that is not ready does not stop the start. A player with an AI stand-in does not stop it either.

Before launch, the lobby shows the DM the count of seats that are not ready, for example `1 seat not ready`. An active player who is not ready counts as a seat that is not ready. A stand-in does not count, because the AI plays that seat. The count hides when every active seat is ready, or when the caller is not the DM.

The owner start route (`POST /api/v1/sessions/:id/start`) checks only the session status. It does not check readiness.

### Embedding the Lit Component

```html
<runefoble-session-lobby
  session-id="sess-star-eater-15"
  campaign-id="camp-star-eater"
  session-title="Session 15: Tomb of the Star-Eater"
  current-user-id="usr-marcus"
  .isDm=${false}
  .canPlay=${true}
  .participants=${partyParticipants}
  .availableCharacters=${myCharacters}
></runefoble-session-lobby>
```

---

## 3. Dispatched Custom Events

The component communicates with the application shell and gateway via composed Custom Events:

### `select-character`
Dispatched when a player selects a character from the dropdown:
```typescript
interface SelectCharacterEventDetail {
  sessionId: string;
  userId: string;
  characterId: string;
  character?: LobbyCharacterOption;
}
```

### `take-seat`
Dispatched when a player clicks "Take a Seat" with a character from the picker (TASK-0889):
```typescript
interface TakeSeatEventDetail {
  sessionId: string;
  characterId: string;
  characterName: string;
  characterClass: string;
}
```

The App Shell (`takeLobbySeat` in `frontend/src/app/session-actions.ts`) sends `POST /api/v1/sessions/{session_id}/join` to the gateway with body `{"character_id", "character_name", "character_class"}`. The gateway forwards the bearer and the body. game_session seats the verified caller and checks `session.participate`. A caller outside the campaign gets the owner's `403`. An unreachable game_session gives `503`. On success, the App Shell reads the lobby roster again. On a refusal, the App Shell shows the error message and keeps the roster.

A caller with no character sees "Create a character to take a seat." and a disabled button.

### `toggle-readiness`
Dispatched when a player checks or unchecks "Ready to Play":
```typescript
interface ToggleReadinessEventDetail {
  sessionId: string;
  userId: string;
  isReady: boolean;
}
```

The App Shell (`toggleReadiness` in `frontend/src/app/session-actions.ts`) sends `POST /api/v1/sessions/{session_id}/lobby/readiness` to the gateway with body `{"is_ready": true}`. The gateway forwards the bearer and the body. game_session stores the readiness in the session aggregate. The player is the verified caller. The body has no player id. The caller needs `session.participate`; a caller without it gets `403`. The route accepts changes only while the session status is `lobby`, and only for a joined player. After the owner saves the change, the gateway sends `{"type": "player_readiness", "userId", "isReady"}` to every session socket. The App Shell reads the roster again. If the write fails, the App Shell shows the error and restores the checkbox.

### `toggle-stand-in`
Dispatched when a player toggles absentee AI stand-in takeover:
```typescript
interface ToggleStandInEventDetail {
  sessionId: string;
  userId: string;
  isAbsent: boolean;
}
```

A player sees the control on their own card. The DM sees it on every seat. The owner decides, through SpiceDB, who may act:

- The seat's own player needs `session.participate`.
- A caller with `session.control` (`campaign#run_session`, the DM) may set any seat.
- Any other caller gets `403`. No role name grants access.

The App Shell calls `POST /api/v1/sessions/{session_id}/seats/{player_id}/stand-in` with `{"is_absent": true|false}`. The gateway forwards the bearer and the body. The owner acts on the seat named in the path.

- **Absent (`is_absent` true)**: game_session records the absence. When the seat has a lobby character, it activates that character's AI stand-in on `character-sheet`. The gateway then sends `{"type": "player_stand_in", "userId", "isAbsent": true}` to every session socket.
- **Back (`is_absent` false)**: game_session releases the stand-in and marks the seat present with its own character. The gateway then sends `{"type": "player_stand_in", "userId", "isAbsent": false}`.

When the DM sets another seat, the owner calls `character-sheet` with the service credential, not the player's bearer (ADR-0015 e). The DM's `session.control` check comes first. A seat with no lobby character records the absence only.

The stand-in state is stored by game_session. After a reload, the lobby reads `is_present` and `is_stand_in_active` from `GET /api/v1/sessions/{session_id}`. The lobby does not keep the stand-in in the page. The gateway does not check the seat itself; it forwards the call and the owner answers `403` for a caller who may not act on the seat.

### `lobby/character`
Taking a seat also stores the seat character as the lobby character. The App Shell calls `POST /api/v1/sessions/{session_id}/lobby/character` with `{"character_id"}` after the join succeeds. game_session hands this character to the AI stand-in when the player leaves.

### `launch-session`
Dispatched when the GM clicks "Launch Session":
```typescript
interface LaunchSessionEventDetail {
  sessionId: string;
  campaignId?: string;
}
```

---

## 4. Backend Session Launch API Flow

When the GM clicks the launch button, the host application executes `POST /api/v1/sessions/:id/start`. The caller needs `session.control` (`campaign#run_session`). A player gets `403`.

```bash
curl -X POST "http://localhost:8004/api/v1/sessions/sess-star-eater-15/start" \
  -H "Authorization: Bearer <DM_JWT>" \
  -H "Content-Type: application/json"
```

**Response (`200 OK`):**
```json
{
  "id": "sess-star-eater-15",
  "status": "active",
  "campaign_id": "camp-star-eater",
  "current_turn": 1,
  "turn_order": ["char-valeros-1", "char-kyra-standin"]
}
```

The start route does not check readiness. Launch follows the Launch Rule in section 2.

Upon successful start, a `runefoble.events.session.started` domain event is broadcast across Redis Streams channel `events:session`, prompting all connected lobby clients to navigate to the active VTT board route `#/campaigns/:campaignId/sessions/:sessionId`.

---

## 5. Scheduling Sessions and Creating Staging Lobbies with `<runefoble-session-modal>`

To create real session entities prior to assembling in the lobby, the campaign detail view equips `<runefoble-session-list>` with `<runefoble-session-modal>`:

1. **Triggering the Modal**: In the campaign detail view (`#/campaigns/:campaignId`), Game Masters click `+ New Session` to open `<runefoble-session-modal>`.
2. **Configuring Session Parameters**:
   - **Session Title**: Descriptive scenario name (e.g. `Chapter 4: The Sunken Vault`).
   - **Initial Status**:
     - `lobby`: Immediately opens a pre-game staging lobby for participant assembly.
     - `upcoming`: Creates a scheduled calendar entry with date/time for future sessions.
   - **Scheduled Date & Time**: Optional ISO-8601 / datetime-local value.
   - **Description & DM Notes**: Scenario briefing, preparation notes, or DM recap.
3. **Event Dispatch & Persistence**:
   - Submitting the form validates input and emits `@create-session` with payload:
     ```typescript
     interface CreateSessionDetail {
       campaignId?: string;
       title: string;
       scheduledAt?: string;
       description?: string;
       status: 'lobby' | 'upcoming';
     }
     ```
   - The App Shell delegates to `AppDataService.createCampaignSession()`, calling `POST /api/v1/campaigns/{campaign_id}/sessions` requiring Zanzibar `run_session` permission. The route creates the game session aggregate in the same call. The returned `id` is the only session id the App Shell stores. It is the UUID that `GET /api/v1/sessions/{id}` accepts (TASK-0706).
   - In fallback/offline mode, newly created sessions are persisted into `FALLBACK_CAMPAIGN_SESSIONS_MAP[campaignId]`, guaranteeing that subsequent `fetchCampaignSessions(campaignId)` reloads preserve newly scheduled sessions.
   - On success, the campaign session list refreshes. If `status === 'lobby'`, the router automatically navigates to `#/campaigns/:campaignId/lobby/:sessionId`.
5. **Initial Staging Lobby Auto-Seeding (TASK-0354)**:
   - Creating a new campaign on the backend (`POST /api/v1/campaigns`) automatically seeds an initial staging lobby (`Session #1: Staging Lobby`, status: `lobby`) and writes the corresponding SpiceDB Zanzibar relationship tuples (`session:{id}#campaign@campaign:{campaign_id}` and `game_session:{id}#campaign@campaign:{campaign_id}`).
   - All campaigns maintain isolated, non-overlapping session rosters with zero hardcoded cross-campaign stubs.

---

## 6. Dynamic Character Selection and Active VTT Hand-off (TASK-0256)

Instead of static placeholders, `<runefoble-session-lobby>` receives available characters dynamically populated from the authenticated user's character roster via `appDataService.fetchLobbyState(campaignId, sessionId)`:
1. **Campaign Prioritization**: Characters assigned to `campaignId` are prioritized at the top of the character selection dropdown.
2. **Selection Propagation**: Selecting a character dispatches `@select-character` (and `@character-selected`). The selection syncs with `RunefobleApp.activeCharacter` only when the caller owns the character (TASK-0972).
3. **Seamless Transition**: When launching the session, the active VTT `<runefoble-character-card>` mounts directly bound to the selected character's name, class, HP, AC, and portrait.

