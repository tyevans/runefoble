# How-To: Manage DM Co-Pilot Whispers and Veto Overrides

This guide explains how human Dungeon Masters (DMs) receive private narrative whispers and intercept, veto, or modify AI-proposed game actions before they mutate the tactical board (ADR-0001, ADR-0002, ADR-0004, ADR-0013).

---

## 1. SpiceDB Zanzibar Authorization

DM Co-Pilot whispers and action vetoes are gated by SpiceDB Zanzibar object authorization (`libs/runefoble_auth/schema/runefoble.zed`). The caller identity comes only from a verified Zitadel bearer token. Headers such as `X-User-Id` and body fields never set it.

The Watcher checks only permissions that the schema defines. Each check uses a name from `runefoble_auth.contract.ACTION_PERMISSIONS`:

| Route | Action | Schema check |
|---|---|---|
| `GET /api/v1/watcher/whispers`, `POST /api/v1/watcher/whispers`, `POST /api/v1/watcher/whispers/generate` | `session.control` on the session | `session:<session_id>#control` (DM, GM, or owner through `campaign->run_session`) |
| `POST /api/v1/watcher/veto`, `approve`, `modify` | `session.control` on the session. `session_id` is required in the body | same as above |
| `GET /api/v1/watcher/actions/pending` | `session.control` | same as above |

To make a user the DM of a session, the setup must write two schema tuples:
- `campaign:<campaign_id>#dungeon_master@user:<user_id>`: the DM relation. `run_session` includes it.
- `session:<session_id>#campaign@campaign:<campaign_id>`: links the session to the campaign. `session.control` walks this link.

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
2. **Action Intercepted**: The action enters `pending` state and emits `runefoble.events.watcher.action_proposed` over Redis Streams (`runefoble.events.watcher`).
3. **DM Adjudication**:
   - **Veto**: The DM halts execution immediately. The action is cancelled, `runefoble.events.watcher.action_vetoed` is published, and board state remains unchanged.
   - **Approve**: The DM bypasses the remaining pause timer to commit the action immediately (`runefoble.events.watcher.action_approved`).
   - **Modify**: The DM edits the description, target, or parameters before committing (`runefoble.events.watcher.action_modified`).
   - **Timeout Expiry**: If the DM does not decide within the pause window, the action automatically commits and executes. `runefoble.events.watcher.action_expired` is published with the original action.

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
></runefoble-dm-whisper-bar>
```

---
