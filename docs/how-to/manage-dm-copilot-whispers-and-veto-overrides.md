# How-To: Manage DM Co-Pilot Whispers and Veto Overrides

This guide explains how human Dungeon Masters (DMs) receive private narrative whispers and intercept, veto, or modify AI-proposed game actions before they mutate the tactical board (ADR-0001, ADR-0002, ADR-0004, ADR-0013).

---

## 1. SpiceDB Zanzibar Authorization

DM Co-Pilot whispers and action vetoes are strictly gated by SpiceDB Zanzibar object authorization (`libs/runefoble_auth/schema/runefoble.zed`).

To access the private DM stream and veto actions:
- The user must hold the `dungeon_master` relation or `run_session` permission on the owning `campaign` resource:
  `campaign:<campaign_id>#dungeon_master@user:<user_id>`.
- Any user without this relation (e.g. standard players or spectators) is denied with HTTP `403 Forbidden`.

```bash
# Example Zanzibar check via header
curl -X GET "http://localhost:8001/api/v1/watcher/whispers?session_id=sess-101&campaign_id=camp-202" \
  -H "X-User-Id: dm_evelyn"
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
   - **Timeout Expiry**: If the DM does not veto within the pause window, the action automatically commits and executes.

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
X-User-Id: dm_evelyn
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
X-User-Id: dm_evelyn
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
X-User-Id: dm_evelyn
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
X-User-Id: dm_evelyn
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
