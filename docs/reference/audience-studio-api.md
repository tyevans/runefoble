# Reference: Audience Studio API

The TypeScript `audience_studio` service (port 8010) runs live spectator polls and the DM approval queue. Governed by ADR-0001 (SpiceDB), ADR-0005 (Kubernetes), ADR-0015 (identity), and TASK-0533.

## Authentication

- Every route needs a Zitadel access token, except the three public paths below.
- **HTTP**: `Authorization: Bearer <token>`.
- **WebSocket**: offer `runefoble.v1` and `runefoble.bearer.<token>` as subprotocols. The service accepts `runefoble.v1` only. It never echoes the bearer protocol. The token never goes in the query string.
- The service verifies RS256 signature, `iss`, `aud`, `exp`, and `sub` against Zitadel's JWKS.
- The actor of every command is the token subject. Request bodies and headers never name the actor.

| Status | Meaning |
|---|---|
| `401 Unauthorized` | No token, or the token fails a check. Response has `WWW-Authenticate: Bearer`. |
| `403 Forbidden` | Token is valid, but SpiceDB denies the `run_session` check on the campaign. |
| `503 Service Unavailable` | The JWKS endpoint, Redis Streams, or PostgreSQL is unavailable. |

### Public paths

| Path | Purpose |
|---|---|
| `GET /healthz` | Liveness |
| `GET /readyz` | Readiness (`503` while Redis or PostgreSQL is down) |
| `GET /ui/manifest` | Microfrontend manifest (ADR-0013) |

## REST Routes (prefix `/api/v1/audience`)

| Method | Path | Actor | Notes |
|---|---|---|---|
| `POST` | `/polls` | Token subject | Creates a poll. Body: `campaign_id`, `title`, `prompt`, `options`, optional `duration_seconds`, `quorum`, `session_id`, `modifier_type`. |
| `GET` | `/polls` | Token subject | Lists polls. Query: `campaign_id`. |
| `GET` | `/polls/{pollId}` | Token subject | Returns one poll. |
| `POST` | `/polls/{pollId}/votes` | Token subject (voter) | Body: `option_id`, optional `channel`. Duplicate votes return `400`. |
| `POST` | `/polls/{pollId}/close` | Token subject | Closes the poll and queues a proposal when quorum is met. |
| `GET` | `/proposals` | Token subject | Lists proposals. Query: `campaign_id`, `status`. |
| `POST` | `/proposals/{proposalId}/approve` | DM (SpiceDB `run_session`) | Approves the proposal. No body. |
| `POST` | `/proposals/{proposalId}/veto` | DM (SpiceDB `run_session`) | Vetoes the proposal. No body. |

Documentation routes `GET /openapi.json` and `GET /docs` also need a token.

## Removed Interfaces (TASK-0533)

| Removed | Replacement |
|---|---|
| `POST /api/v1/audience/auth/tuples` | Returns `404`. Grant DM relations through SpiceDB's write API. |
| Body field `dm_user_id` on approve and veto | Ignored. The token subject is the actor. |
| Body field `voter_id` on votes | Ignored. The token subject is the voter. |
| Header `x-user-id` | Ignored. |
| Fallback actor `dm-user` | Removed. A request without a verified token gets `401`. |
| WebSocket fields `userId` and `role` | Ignored. The handshake principal is the actor. |

## WebSocket

`GET /ws/audience/{campaignId}` (upgrade). The handshake must carry a verified bearer subprotocol. A refused handshake returns `401` and never opens.

Client actions: `subscribe`, `ping`, `cast_vote` (`pollId`, `optionId`, optional `channel`), `approve_proposal` (`proposalId`), `veto_proposal` (`proposalId`).

Server frames: `connected`, `subscribed`, `poll_started`, `vote_cast`, `poll_completed`, `proposal_queued`, `proposal_approved`, `proposal_vetoed`, `error`, `pong`.

## Configuration

| Variable | Required | Notes |
|---|---|---|
| `RUNEFOBLE_ZITADEL_ISSUER` | Yes | Must equal the token `iss`. The service exits at start-up when unset. |
| `RUNEFOBLE_ZITADEL_AUDIENCE` | Yes | Must equal the token `aud`. The service exits at start-up when unset. |
| `RUNEFOBLE_ZITADEL_JWKS_URL` | No | When unset, the service reads `jwks_uri` from OIDC discovery at start-up. |
| `RUNEFOBLE_SPICEDB_ENDPOINT` | Yes in deployment | Base URL of SpiceDB HTTP API. Without it, every DM check is denied. |
| `RUNEFOBLE_SPICEDB_PRESHARED_KEY` | Yes outside tests | Operator secret. No default. |
| `RUNEFOBLE_DATABASE_URL`, `REDIS_URL` | Yes outside tests | Event store and Redis Streams. |

The Helm chart sets the Zitadel variables from `services.audienceStudio` and the Zitadel values. Governing docs: [How-To: Orchestrate Audience Chaos Polls](../how-to/orchestrate-audience-chaos-polls.md), [How-To: Verify Identity in FastAPI and WebSockets](../how-to/verify-identity-in-fastapi-and-websockets.md).
