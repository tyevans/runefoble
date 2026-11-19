# How-To: Manage DM Co-Pilot Whispers and Veto Overrides

This guide explains how human Dungeon Masters (DMs) receive private narrative whispers and intercept, veto, or modify AI-proposed game actions before they mutate the tactical board (ADR-0001, ADR-0002, ADR-0004, ADR-0013).

---

## 1. SpiceDB Zanzibar Authorization

DM Co-Pilot whispers and action vetoes are gated by SpiceDB Zanzibar object authorization (`libs/runefoble_auth/schema/runefoble.zed`). The caller identity comes only from a verified Zitadel bearer token. Headers such as `X-User-Id` and body fields never set it.

The Watcher checks only permissions that the schema defines. Each check uses a name from `runefoble_auth.contract.ACTION_PERMISSIONS`:

| Route | Action | Schema check |
|---|---|---|
| `GET /api/v1/watcher/whispers`, `POST /api/v1/watcher/whispers`, `POST /api/v1/watcher/whispers/generate` | `session.control` on the session | `game_session:<session_id>#control` (DM, GM, or owner through `campaign->run_session`) |
| `POST /api/v1/watcher/veto`, `approve`, `modify` | `session.control` on the session. `session_id` is required in the body | same as above |
| `GET /api/v1/watcher/actions/pending` | `session.control` | same as above |

To make a user the DM of a session, the setup must write two schema tuples:
- `campaign:<campaign_id>#dungeon_master@user:<user_id>`: the DM relation. `run_session` includes it.
- `game_session:<session_id>#campaign@campaign:<campaign_id>`: links the session to the campaign. `session.control` walks this link.

A user without the DM role gets HTTP `403 Forbidden`. A missing or invalid bearer token gets HTTP `401`. The Watcher does not return `200` for an unknown principal.

If SpiceDB is unreachable, the route returns HTTP `503` with `error: authorization_unavailable`. It never treats the failure as a denial or as an allow. If a check names a type, relation, or permission that the schema does not define, the route returns HTTP `500` with an `error_id`. The full error is in the service log under that id.

```bash
# Veto a pending action as the DM. The token subject must hold the DM role.
curl -X POST "http://localhost:8001/api/v1/watcher/veto" \
  -H "Authorization: Bearer $DM_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"action_id": "act-1", "session_id": "sess-101", "campaign_id": "camp-202", "reason": "Too harsh"}'
```

---

## 2. Pre-Execution Veto Interceptor Window

When The Watcher proposes an AI game action (e.g., monster movement, offensive spellcast, or tactical ambush):
1. **Pause Window**: The action is registered with a configurable pre-execution pause window (default `2000ms`, `pause_window_ms`).
2. **Action Intercepted**: The action enters `pending` state. The pending-action aggregate stores it. Read it with `GET /api/v1/watcher/actions/pending`.
3. **DM Adjudication**:
   - **Veto**: The DM halts execution immediately. The action is cancelled, the pending-action aggregate records the veto, and board state remains unchanged.
   - **Approve**: The DM bypasses the remaining pause timer to commit the action immediately. The aggregate records the approval.
   - **Modify**: The DM edits the description, target, or parameters before committing. The aggregate records the modification.
   - **Timeout Expiry**: If the DM does not decide within the pause window, the action automatically commits and executes. The aggregate records the expiry.

Pending actions, whispers, and open disambiguations are event-sourced aggregates (`WatcherPendingActions`, `WatcherWhispers`, `WatcherDisambiguations`). A service restart keeps them. At start-up, the service re-arms the expiry timer of every open action from its stored deadline, so an action whose window elapsed during the outage expires at start-up.

Decision errors:
- An action id that the session does not hold returns `404`. No placeholder action is created.
- A veto, approve, or modify on an action that is already vetoed, approved, or executed returns `409`.
- A `session_id` is required for `veto`, `approve`, `modify`, and `GET /api/v1/watcher/actions/pending`.
- An in-process execute hook that fails on approve is logged. The failure is returned as `execution_error` in the response.

---

## 3. Public REST APIs

### Propose Action
```http
POST /api/v1/watcher/actions/propose
Content-Type: application/json

{
  "session_id": "sess-101",
  "campaign_id": "camp-202",
  "actor_name": "Goblin Skulker",
  "action_type": "attack",
  "description": "Dashes from shadow to strike Merisiel",
  "target": "Merisiel",
  "parameters": { "damage": 6 },
  "pause_window_ms": 2000
}
```

### Veto Action
```http
POST /api/v1/watcher/veto
Authorization: Bearer <dm_evelyn access token>
Content-Type: application/json

{
  "action_id": "act-9182a",
  "session_id": "sess-101",
  "campaign_id": "camp-202",
  "reason": "Player was in stealth cover; goblin could not detect"
}
```

### Approve Action
```http
POST /api/v1/watcher/approve
Authorization: Bearer <dm_evelyn access token>
Content-Type: application/json

{
  "action_id": "act-9182a",
  "session_id": "sess-101",
  "campaign_id": "camp-202"
}
```

### Modify Action
```http
POST /api/v1/watcher/modify
Authorization: Bearer <dm_evelyn access token>
Content-Type: application/json

{
  "action_id": "act-9182a",
  "session_id": "sess-101",
  "campaign_id": "camp-202",
  "target": "Valeros Shield",
  "parameters": { "damage": 2 },
  "auto_approve": true
}
```

### Get Paginated Whispers
```http
GET /api/v1/watcher/whispers?session_id=sess-101&campaign_id=camp-202&page=1&limit=20&whisper_type=monster_tactics
Authorization: Bearer <dm_evelyn access token>
```

### Send an Audience Narration to the Table
An approved audience modifier leads The Watcher to record one whisper of type `audience_narration` for the DM. The whisper stays pending until the DM acts. The DM sends it to the table with:
```http
POST /api/v1/watcher/whispers/{whisper_id}/dispatch
Authorization: Bearer <dm_evelyn access token>
Content-Type: application/json

{
  "session_id": "sess-101",
  "campaign_id": "camp-202",
  "text": "The bell tolls once. Every torch in the crypt gutters."
}
```
- `text` is optional. Without it, the recorded narration is sent as written.
- The route requires `session.control` (DM). A player gets `403`.
- The route publishes `runefoble.events.watcher.narrative_dispatched` on `runefoble.events.watcher`, then marks the whisper with `metadata.dispatched: true`. The event is published first, so a failed publish returns `503` and the whisper stays pending.
- A second dispatch of the same whisper returns `409`. A whisper of another type returns `409`. An unknown whisper returns `404`.

### Audience Narration Failures
When the inference worker cannot narrate an approved modifier, The Watcher records a whisper of type `narration_unavailable`. Its `content` holds a short reason. It never holds narration text, and it cannot be dispatched. The same happens when the worker answers with `degraded: true`, or when the Watcher runs on the `heuristic` engine. Nothing is sent to the table. The DM decides what to do next.

---

## 4. Using the `<runefoble-dm-whisper-bar>` Microfrontend

The `<runefoble-dm-whisper-bar>` Lit component is vendored by `@runefoble/the-watcher-ui` and exposed in `the_watcher`'s `/ui/manifest`.

```html
<runefoble-dm-whisper-bar
  sessionId="sess-101"
  campaignId="camp-202"
  .pendingAction="${activePendingAction}"
  .whispers="${dmWhispersList}"
  @action-approved="${(e) => approveAction(e.detail.actionId)}"
  @action-vetoed="${(e) => vetoAction(e.detail.actionId, e.detail.reason)}"
  @action-modified="${(e) => modifyAction(e.detail)}"
  @narration-send="${(e) => sendNarration(e.detail)}"
></runefoble-dm-whisper-bar>
```

An `audience_narration` whisper that is not yet sent shows a **Send to table** button. The button fires `narration-send` with `detail.whisperId`, `detail.text`, `detail.sessionId` and `detail.campaignId`. The host posts to the dispatch route above and then sets `metadata.dispatched` on that whisper. A sent narration shows **Sent to table**. A `narration_unavailable` whisper shows a notice with its reason, and no button.

---
