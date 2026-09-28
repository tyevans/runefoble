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

- **Modular Styles Architecture**: Scoped styles are decomposed into focused submodules under `services/game_session/ui/src/lobby/styles/` (`base.styles.ts`, `roster.styles.ts`, `controls.styles.ts`), composed via `sessionLobbyStyles` in `runefoble-session-lobby.styles.ts` (keeping all style modules strictly < 150 lines per Hard Invariant 6).

### Component Attributes & Properties

| Attribute / Property | Type | Description |
|---|---|---|
| `session-id` | `string` | Unique session identifier UUID |
| `campaign-id` | `string` | Owning campaign identifier |
| `session-title` | `string` | Display title for the game session |
| `current-user-id` | `string` | User ID of the logged-in participant |
| `participants` | `LobbyParticipant[]` | Array of participant objects with readiness state |
| `available-characters` | `LobbyCharacterOption[]` | List of owned characters available for selection |
| `is-dm` | `boolean` | Flag indicating whether current user has GM authority |
| `can-launch` | `boolean` | Zanzibar-derived permission to launch the session |
| `is-loading` | `boolean` | Loading indicator disabling interactive triggers |

### Embedding the Lit Component

```html
<runefoble-session-lobby
  session-id="sess-star-eater-15"
  campaign-id="camp-star-eater"
  session-title="Session 15: Tomb of the Star-Eater"
  current-user-id="usr-marcus"
  .isDm=${false}
  .canLaunch=${false}
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

### `toggle-readiness`
Dispatched when a player checks or unchecks "Ready to Play":
```typescript
interface ToggleReadinessEventDetail {
  sessionId: string;
  userId: string;
  isReady: boolean;
}
```

### `toggle-stand-in`
Dispatched when a player or GM toggles absentee AI stand-in takeover:
```typescript
interface ToggleStandInEventDetail {
  sessionId: string;
  userId: string;
  isAbsent: boolean;
}
```

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

When the GM clicks the launch button, the host application executes `POST /api/v1/sessions/:id/start`:

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

Upon successful start, a `SessionStarted` domain event is broadcast across Redis Streams channel `events:session`, prompting all connected lobby clients to navigate to the active VTT board route `#/campaigns/:campaignId/sessions/:sessionId`.

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
   - The App Shell delegates to `AppDataService.createCampaignSession()`, calling `POST /api/v1/campaigns/{campaign_id}/sessions` requiring Zanzibar `run_session` permission.
   - On success, the campaign session list refreshes. If `status === 'lobby'`, the router automatically navigates to `#/campaigns/:campaignId/lobby/:sessionId`.

---

## 6. Dynamic Character Selection and Active VTT Hand-off (TASK-0256)

Instead of static placeholders, `<runefoble-session-lobby>` receives available characters dynamically populated from the authenticated user's character roster via `appDataService.fetchLobbyState(campaignId, sessionId)`:
1. **Campaign Prioritization**: Characters assigned to `campaignId` are prioritized at the top of the character selection dropdown.
2. **Selection Propagation**: Selecting a character dispatches `@select-character` (and `@character-selected`), synchronizing the selection with `RunefobleApp.activeCharacter`.
3. **Seamless Transition**: When launching the session, the active VTT `<runefoble-character-card>` mounts directly bound to the selected character's name, class, HP, AC, and portrait.

