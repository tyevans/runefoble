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
| `403 Forbidden` | Token is valid, but SpiceDB denies the permission that the route needs. See [Permissions](#permissions). |
| `404 Not Found` | The poll or proposal does not exist. Checked before the permission. |
| `503 Service Unavailable` | The JWKS endpoint, SpiceDB, Redis Streams, or PostgreSQL is unavailable. The service fails closed. |

## Permissions

Each action checks one permission on the `audience_poll` object, or on the `campaign` object for poll creation and the WebSocket handshake. The names come from `libs/runefoble_auth/schema/runefoble.zed`. Role names never appear in the service.

| Action | Check (SpiceDB) |
|---|---|
| Create a poll | `campaign:<campaign_id>#run_session` |
| List or read a poll | `audience_poll:<poll_id>#view` |
| Vote (HTTP or WebSocket `cast_vote`) | `audience_poll:<poll_id>#vote` |
| Close a poll | `audience_poll:<poll_id>#moderate` |
| Approve (HTTP or WebSocket) | `audience_poll:<poll_id>#approve` |
| Veto (HTTP or WebSocket) | `audience_poll:<poll_id>#veto` |
| Open WebSocket for a campaign | `campaign:<campaign_id>#view` |

A poll links to its campaign through the `campaign` relation. The service writes that relation when the poll is created.

**Proposal parameters.** A proposal in a response carries `parameters`, `description`, and `modifierType` only for a caller with `audience_poll.approve`. Other callers get `id`, `pollId`, `campaignId`, `sessionId`, `title`, `status`, `createdAt`, `reviewedBy`, and `reviewedAt`.

**Broadcasts.** `proposal_queued` reaches only sockets whose principal has `audience_poll.approve`. Other events reach every socket that can view the campaign. Each socket gets the same redaction as the HTTP routes.

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
| `GET` | `/polls` | Token subject | Lists the polls the caller can view. Query: `campaign_id`. |
| `GET` | `/polls/{pollId}` | Token subject (`view`) | Returns one poll. |
| `POST` | `/polls/{pollId}/votes` | Token subject (`vote`) | Body: `option_id`, optional `channel`. Duplicate votes return `400`. |
| `POST` | `/polls/{pollId}/close` | Token subject (`moderate`) | Closes the poll and queues a proposal when quorum is met. |
| `GET` | `/proposals` | Token subject (`view`) | Lists proposals of polls the caller can view. Query: `campaign_id`, `status`. |
| `POST` | `/proposals/{proposalId}/approve` | Token subject (`approve`) | Approves the proposal. No body. |
| `POST` | `/proposals/{proposalId}/veto` | Token subject (`veto`) | Vetoes the proposal. No body. |

Documentation routes `GET /openapi.json` and `GET /docs` also need a token.

## Gateway Routes (TASK-0439)

Clients reach these routes through the unified gateway on port 8000. The gateway verifies the token, then forwards the request with the same token. The service checks each permission. The gateway passes the service's `401`, `403` and `404` answers on unchanged. An unreachable service returns `503` from the gateway. A `5xx` answer from the service returns `502` from the gateway, with the upstream name. The same paths and methods as the REST table above apply, with the prefix `/api/v1/audience`. The WebSocket path `/ws/audience/{campaignId}` is relayed the same way.

## Removed Interfaces (TASK-0533)

| Removed | Replacement |
|---|---|
| `POST /api/v1/audience/auth/tuples` | Returns `404`. Grant campaign relations through SpiceDB's write API. |
| Body field `dm_user_id` on approve and veto | Ignored. The token subject is the actor. |
| Body field `voter_id` on votes | Ignored. The token subject is the voter. |
| Header `x-user-id` | Ignored. |
| Fallback actor `dm-user` | Removed. A request without a verified token gets `401`. |
| WebSocket fields `userId` and `role` | Ignored. The handshake principal is the actor. |

## WebSocket

`GET /ws/audience/{campaignId}` (upgrade). The handshake must carry a verified bearer subprotocol, and the principal needs `campaign:<campaignId>#view`. A refused handshake returns `401` (no token) or `403` (no campaign view) and never opens.

Client actions: `subscribe`, `ping`, `cast_vote` (`pollId`, `optionId`, optional `channel`), `approve_proposal` (`proposalId`), `veto_proposal` (`proposalId`).

Server frames: `connected`, `subscribed`, `poll_started`, `vote_cast`, `poll_completed`, `proposal_queued`, `proposal_approved`, `proposal_vetoed`, `error`, `pong`.

**Error frames.** A failed client frame gets one `error` frame with a fixed `code` and a `message`. The socket stays open.

| `code` | When | `message` |
|---|---|---|
| `invalid_message` | The frame is not JSON, has no string `action`, or lacks a field the action needs. | Names the problem. |
| `unknown_action` | The `action` is not in the client action list. | Names the action. |
| `forbidden` | The principal lacks the schema permission (`403`). | The permission message, as the HTTP route shows it. |
| `rejected` | A domain rule or the identity check refused the command (`400`, `401`, `404` or `409`). | The domain message, as the HTTP route shows it. |
| `internal_error` | Any other failure, including a SpiceDB or Redis fault. | A fixed text. No internal detail. The server logs the cause. |

## Configuration

| Variable | Required | Notes |
|---|---|---|
| `RUNEFOBLE_ZITADEL_ISSUER` | Yes | Must equal the token `iss`. The service exits at start-up when unset. |
| `RUNEFOBLE_ZITADEL_AUDIENCE` | Yes | Must equal the token `aud`. The service exits at start-up when unset. |
| `RUNEFOBLE_ZITADEL_INTERNAL_URL` | No | In-cluster Zitadel origin. Discovery and JWKS requests go here with `Host` set to the issuer host. When unset, the service reads discovery from the issuer at start-up. |
| `RUNEFOBLE_SPICEDB_ENDPOINT` | Yes | SpiceDB gRPC address. Use `host:port` (plaintext gRPC, the in-cluster form), `grpc://host:port` (plaintext), or `https://host:port` (TLS). Any other scheme stops start-up. The service exits at start-up when unset. |
| `RUNEFOBLE_SPICEDB_PRESHARED_KEY` | Yes | Operator secret. Sent as the bearer token on every SpiceDB call. No default. The service exits at start-up when it is unset or empty. `NODE_ENV` does not change this. |
| `RUNEFOBLE_EVENT_STORE_BACKEND` | No | `postgresql` (the Helm value) or unset. Any other value, `memory` too, stops start-up. Same flag name as the Python services. |
| `RUNEFOBLE_DATABASE_URL` | Yes | PostgreSQL event store. The service exits at start-up when it is unset. `NODE_ENV` does not change this. |
| `RUNEFOBLE_REDIS_URL` | Yes | Redis Streams. Must start with `redis://` or `rediss://`. The service exits at start-up when it is unset or has another scheme, such as `mock://`. `NODE_ENV` does not change this. |

Production code has no in-memory event store and no mock stream bus (ADR-0015 decision f). Tests inject fakes from `services/audience_studio/test/fakes/` through the `createAdapters` option of `buildServer`.

The Helm chart sets the Zitadel variables from `services.audienceStudio` and the Zitadel values. Governing docs: [How-To: Orchestrate Audience Chaos Polls](../how-to/orchestrate-audience-chaos-polls.md), [How-To: Verify Identity in FastAPI and WebSockets](../how-to/verify-identity-in-fastapi-and-websockets.md).
