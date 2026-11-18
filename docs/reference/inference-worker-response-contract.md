# Inference Worker Response Contract

This page defines the HTTP response contract of the inference worker (`services/inference_worker`). It covers backend failure and response provenance.

## Endpoints

| Method | Path | Response model |
|---|---|---|
| POST | `/inference/v1/intent` | `IntentParseResponse` |
| POST | `/inference/v1/dm-narration` | `DMNarrationResponse` |
| POST | `/inference/v1/stand-in-action` | `StandInActionResponse` |

## Authentication

Every `/inference/v1/*` route requires the service credential. The caller sends:

```http
X-Runefoble-Service-Credential: <RUNEFOBLE_SERVICE_CREDENTIAL>
```

| Case | Response |
|---|---|
| No header, or a wrong value | `401` with body `{"error": "unauthorized", "message": ...}` |
| The Zitadel user token of a player in `Authorization` | `401`. A user token is not a service credential. |
| The configured credential | The route runs. |

The worker refuses to start when `RUNEFOBLE_SERVICE_CREDENTIAL` is unset or blank. The worker sends no CORS headers. The `/healthz` and `/health` routes stay open for probes.

## Provenance Fields

Each successful response includes these fields.

| Field | Type | Meaning |
|---|---|---|
| `source` | `"llm"`, `"heuristic"`, or `"mock"` | The path that produced the result. |
| `degraded` | boolean | `true` when a fallback path produced the result. |

Values of `source`:

- `llm`: A real model backend returned usable output.
- `heuristic`: The model returned output with no action. The worker used regex keyword rules instead. `degraded` is `true`. Only the intent endpoint uses this value.
- `mock`: The operator selected the `mock` backend. The output is canned. `degraded` is `false`.

## Backend Failure

The worker never returns substitute text for a failed backend. A failure returns HTTP 503:

```json
{"error": "backend_unavailable", "backend": "openai_compatible"}
```

The `backend` value is the name of the selected backend, `openai_compatible` or `ollama`. The selected server failed or returned no usable output.

A narration or stand-in response also returns 503 when the model output has no usable JSON. An intent response does not. For intent, the worker uses the regex heuristic and sets `source` to `heuristic`.

## Backend Selection

Set the backend with `RUNEFOBLE_WORKER_BACKEND`. The worker reads the value once, in the app lifespan, and builds one engine port from it (`docs/how-to/add-an-engine-port-adapter.md`):

| Value | Behaviour |
|---|---|
| `openai_compatible` | Calls the configured OpenAI-compatible endpoint. The default. |
| `ollama` | Calls the local Ollama endpoint. |
| `mock` | Returns canned output. Use only for tests and offline checks. |

At start-up the worker calls the selected server once. `openai_compatible` calls `GET {base_url}/models`. `ollama` calls `GET {base_url}/api/tags`. When the server does not answer with HTTP 200, the worker refuses to start. A value outside the table also stops start-up, and the error names the allowed values. No request path probes a backend.

## Redis Streams Results

The Redis consumer publishes one result entry for each message to `RUNEFOBLE_WORKER_REDIS_STREAM_OUT`. Every entry has these fields:

- `correlation_id`: the request `correlation_id`. The message ID is used when the request has none.
- `task_type`: the request `type`. The value is `unknown` when the request has no type.
- `status`: `ok` or `error`.

When `status` is `ok`, the `result` field holds a JSON object:

- `parse_intent`: `{"action": <ParsedAction>, "source": ..., "degraded": ...}`
- `generate_narration` and `stand_in_action`: the same shape as the HTTP response body.

When `status` is `error`, the `error` field holds the failure text. The failure can be an unknown task type, a missing `type` or `payload` field, or a backend failure.

The consumer acknowledges each message after it publishes the result. A message stays pending only when the Redis write fails. That failure is logged.

## Stand-In Guardrails

`POST /inference/v1/stand-in-action` accepts an optional `guardrails` object. The Watcher sends it when `POST /api/v1/watcher/stand-in/act` receives a policy. The object uses the `StandInGuardrailPolicy` model (`libs/runefoble_platform/src/runefoble_platform/stand_in_guardrails.py`). Its fields are `preserve_spell_slots`, `protect_allies`, `protect_ally_hp_threshold`, `risk_threshold`, `avoid_melee`, `permadeath_safeguard`, and `custom_priorities`.

- Unknown fields return HTTP 422. Both the worker and The Watcher apply this rule.
- A field that is omitted has no effect. A missing `guardrails` object means that no policy is active.
- The worker sets `guardrails_applied` to the names of the guardrails that the decision enforced. The response never echoes the input list.
- In `mock` mode, the worker enforces `protect_allies` and `avoid_melee` in its canned rules. A name is listed only when its rule fires.
- In `llm` mode, the model declares the guardrails it followed in `guardrails_applied`. The worker keeps only the names that the request activated.

The Watcher returns the worker's `guardrails_applied` list in its `StandInAction` response.

## The Watcher Routes

The Watcher (`services/the_watcher`) calls the worker for three routes. Each route passes the
worker result through with its `source` and `degraded` fields. The Watcher never returns a
canned or template result for a failed worker call.

Configuration:

| Variable | Use |
|---|---|
| `RUNEFOBLE_INFERENCE_URL` | Base URL of the inference worker. When unset, speech and stand-in use the local rule engine. Narration returns 503. |
| `RUNEFOBLE_BOARD_STATE_URL` | Base URL of the board state service. Speech reads the session board to send `visible_tokens`. |

| Watcher route | Worker call | Result fields |
|---|---|---|
| `POST /api/v1/watcher/intent` (and `transcribe-and-act`) | `/inference/v1/intent` | `source`, `degraded`. `confidence` is `null` when the worker omits it. |
| `POST /api/v1/watcher/stand-in/act` | `/inference/v1/stand-in-action` | `source`, `degraded`, `guardrails_applied` |
| `POST /api/v1/watcher/narrate` | `/inference/v1/dm-narration` | `source`, `degraded` |

Speech sends the session's tokens as `visible_tokens`. A session with no board sends an empty list.

Error responses from The Watcher:

| Condition | Watcher response |
|---|---|
| Worker returns 200 | Result built from the worker body. |
| Worker returns 503 | HTTP 503 with `detail: {"error": "backend_unavailable", "backend": <worker backend>}`. |
| Worker unreachable | HTTP 503 with `detail: {"error": "backend_unavailable", "backend": "inference_worker"}`. |
| Other worker status | HTTP 502 with `detail: {"error": "inference_worker_error", "status": <code>}`. |
| Board state unreadable, or `RUNEFOBLE_BOARD_STATE_URL` unset on the speech path | HTTP 503 with `detail: {"error": "backend_unavailable", "backend": "board_state"}`. |
| `RUNEFOBLE_INFERENCE_URL` unset on the narrate route | HTTP 503 with `detail: {"error": "backend_unavailable", "backend": "inference_worker"}`. |

Required request fields. A missing field returns HTTP 422:

- Stand-in: `session_id`, `campaign_id`, `scene_context`.
- Narrate: `session_id`, `campaign_id`, `scene_environment`, `tone`.
