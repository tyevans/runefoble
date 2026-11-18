# How-To: Orchestrate Audience Chaos Polls and Live Interactivity

This guide explains how to configure and orchestrate live audience chaos polls, ingest spectator votes across streaming channels (Twitch, YouTube, web), and manage DM approval queues using the TypeScript `audience_studio` microservice (ADR-0001, ADR-0005, ADR-0006, ADR-0007, ADR-0013).

---

## 1. SpiceDB Zanzibar Object Authorization

Audience polls and chaos modifier approvals are guarded by SpiceDB Zanzibar permissions (`libs/runefoble_auth/schema/runefoble.zed`):

- **Identity**: Every route needs `Authorization: Bearer <Zitadel access token>`. The service verifies the RS256 signature, `iss`, `aud`, and `exp` against Zitadel's JWKS. Without a valid token the service returns `401 Unauthorized`. The actor of every command is the token subject (`sub`). Body fields and headers never name the actor.
- **Spectator / Viewer**: Any user holding the `spectator`, `player`, or `view` relation on `campaign:<campaign_id>` can view active polls and cast votes. The voter is the token subject.
- **Dungeon Master / Moderation**: Approving or vetoing modifier proposals requires `dungeon_master`, `game_master`, or `owner` relation (`run_session` permission) on `campaign:<campaign_id>`. The service asks SpiceDB for this check. It holds no local role or grant table.
- Unauthorized approval attempts return HTTP `403 Forbidden`.
- Grant the DM relation in SpiceDB through its write API (`POST /v1/relationships/write`), not through Audience Studio. Audience Studio has no grant route. `POST /api/v1/audience/auth/tuples` was removed in TASK-0533 and returns `404 Not Found`.

---

## 2. Ingesting Chaos Polls and Votes

### Create a Poll
Initialize a new live chaos poll with a vote duration and quorum threshold:

```http
POST /api/v1/audience/polls
Content-Type: application/json

{
  "campaign_id": "camp-alpha",
  "session_id": "sess-beta",
  "title": "Wild Magic Surge",
  "prompt": "Which environmental effect should hit the battlefield?",
  "options": [
    "Slick Ice Floor (Difficult Terrain)",
    "Healing Geyser (+10 HP Aura)",
    "Gravity Reversal (Floating Tokens)"
  ],
  "duration_seconds": 60,
  "quorum": 5
}
```

The service publishes a CloudEvents 1.0 `runefoble.events.audience.poll_started` event to Redis Streams (`runefoble.events.audience`). It then stores the poll. If Redis is unavailable, the request fails with HTTP `503 Service Unavailable`, and no poll is stored.

### Cast Spectator Votes
High-frequency spectator votes can be submitted from streaming chat bots or the UI:

```http
POST /api/v1/audience/polls/{poll_id}/votes
Authorization: Bearer <spectator access token>
Content-Type: application/json

{
  "option_id": "opt_1",
  "channel": "twitch"
}
```

The voter is the token subject. Duplicate votes from the same subject are rejected with HTTP `400 Bad Request`. A vote on an unknown poll returns `404 Not Found`. A vote after the poll window ends returns `400 Bad Request`.

---

## 3. Quorum Aggregation & DM Approval Queue

When a poll duration expires (or is explicitly closed via `POST /api/v1/audience/polls/{poll_id}/close`):
1. **Vote Tallying**: The system determines the winning option with the highest vote count.
2. **Quorum Verification**:
   - If `total_votes >= quorum`, `quorum_met` is marked `true`, and an `AudienceModifierProposal` is enqueued in status `pending`.
   - `runefoble.events.audience.poll_completed` and `runefoble.events.audience.modifier_proposed` are emitted over Redis Streams.
3. **DM Moderation**:
   - The DM inspects pending proposals via `GET /api/v1/audience/proposals?campaign_id={id}`.
   - The DM approves the proposal:
     ```http
     POST /api/v1/audience/proposals/{proposal_id}/approve
     Authorization: Bearer <DM access token>
     ```
   - Emits `runefoble.events.audience.modifier_approved` with `approved: true`. Gameplay does not apply the chaos effect yet. The subscriber that applies it is tracked in TASK-0441.
   - Alternatively, the DM exercises veto power via `POST /api/v1/audience/proposals/{proposal_id}/veto`. A veto emits the same event type with `approved: false`.
   - A proposal can be decided once. A second approve or veto returns `400 Bad Request`.

---

## 4. Live WebSocket Streaming (`/ws/audience/{campaign_id}`)

Clients and DM dashboards connect to `/ws/audience/{campaign_id}` for sub-500ms broadcast updates:

1. **Connection & Handshake**: Offer two subprotocols: `runefoble.v1` and `runefoble.bearer.<access token>`. The service verifies the token before it accepts the socket. A refused handshake returns `401` and never opens. Never put the token in the query string.
   ```json
   { "action": "subscribe" }
   ```
2. **Live Feed Messages**:
   - `poll_started`: New chaos poll opened.
   - `vote_cast`: Real-time percentage update.
   - `poll_completed`: Quorum and winner announced.
   - `proposal_queued`: Proposal added to DM queue.
   - `proposal_approved` / `proposal_vetoed`: Moderation resolution.
3. **DM WebSocket Approval**:
   ```json
   {
     "action": "approve_proposal",
     "proposalId": "prop-uuid-1234"
   }
   ```

---

## 5. Durability, Recovery, and Readiness

Poll and proposal state is stored as event streams in PostgreSQL (table `audience_studio_events`). The service keeps no poll state in memory.

- **Required configuration**: set `RUNEFOBLE_DATABASE_URL` and `REDIS_URL`. Outside `NODE_ENV=test`, the service exits at start-up when either one is missing or unreachable.
- **Restart**: open polls and pending proposals load from the store. Each open poll closes at its stored deadline. A poll whose window ended while the service was down closes at start-up and publishes `poll_completed`.
- **Publish failure**: a command that cannot publish is rejected. The HTTP route returns `503 Service Unavailable`. The WebSocket route sends an `error` frame. No state changes.
- **Redis outage**: the Redis client reconnects with a backoff of up to five seconds. Writes resume without a restart.
- **Readiness**: `GET /readyz` returns `503` with a `dependencies` object while Redis or PostgreSQL is unavailable. Liveness (`GET /healthz`) stays `200`.

---

## 6. Microfrontend Embedding

Embed the vendored `<runefoble-audience-studio>` Lit element into streaming overlays or DM views:

```html
<script type="module" src="/path/to/@runefoble/audience-studio-ui"></script>

<runefoble-audience-studio
  campaignId="camp-alpha"
  sessionId="sess-beta"
  userId="dm-alice"
  isDM="true"
  wsConnected="true"
></runefoble-audience-studio>
```
