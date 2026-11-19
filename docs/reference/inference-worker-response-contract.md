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

The worker refuses to start when `RUNEFOBLE_SERVICE_CREDENTIAL` is unset or blank. The worker sends no CORS headers. The `/healthz` routes stay open for probes.

## Provenance Fields

Each successful response includes these fields.

| Field | Type | Meaning |
|---|---|---|
| `source` | `"llm"` | The engine that produced the result. Only a model engine produces results. |

`source` is always `llm`. The worker has no keyword rules and no canned output. Each route returns
model output or `503`.

## Backend Failure

The worker never returns substitute text for a failed backend. A failure returns HTTP 503:

```json
{"error": "backend_unavailable", "backend": "openai_compatible"}
```

The `backend` value is the name of the selected backend, `openai_compatible` or `ollama`. The selected server failed or returned no usable output.

A route also returns 503 when the model output has no usable JSON, or when the output lacks a required field. The required fields are:

| Route | Required field |
|---|---|
| `/inference/v1/intent` | `action_type` |
| `/inference/v1/dm-narration` | `narration` |
| `/inference/v1/stand-in-action` | `action_type` |

The worker checks each field with `require_field` (`inference_worker/model_output.py`). It never fills a missing field with a default or a keyword rule.

## Backend Selection

Set the backend with `RUNEFOBLE_WORKER_BACKEND`. The worker reads the value once, in the app lifespan, and builds one engine port from it (`docs/how-to/add-an-engine-port-adapter.md`):

| Value | Behaviour |
|---|---|
| `openai_compatible` | Calls the configured OpenAI-compatible endpoint. The default. |
| `ollama` | Calls the local Ollama endpoint. |

The value `mock` is refused in every environment. The worker has no canned engine. Tests use a loopback OpenAI-compatible server instead (`tests/helpers/fake_openai_server.py`).

At start-up the worker calls the selected server once. `openai_compatible` calls `GET {base_url}/models`. `ollama` calls `GET {base_url}/api/tags`. When the server does not answer with HTTP 200, the worker refuses to start. A value outside the table also stops start-up, and the error names the allowed values. No request path probes a backend.

## Redis Streams

The worker has no Redis Streams consumer in this release. Its Helm Deployment sets `RUNEFOBLE_WORKER_REDIS_ENABLED` to `false`. The Watcher calls the worker over HTTP only.

## Stand-In Guardrails

`POST /inference/v1/stand-in-action` accepts an optional `guardrails` object. The Watcher sends it when `POST /api/v1/watcher/stand-in/act` receives a policy. The object uses the `StandInGuardrailPolicy` model (`libs/runefoble_platform/src/runefoble_platform/stand_in_guardrails.py`). Its fields are `preserve_spell_slots`, `protect_allies`, `protect_ally_hp_threshold`, `risk_threshold`, `avoid_melee`, `permadeath_safeguard`, and `custom_priorities`.

- Unknown fields return HTTP 422. Both the worker and The Watcher apply this rule.
- `guardrails_applied` holds only `GuardrailName` values: `preserve_spell_slots`, `protect_allies`, `avoid_melee`, and `custom_priorities`. The local Watcher engine and the worker report the same names.
- A field that is omitted has no effect. A missing `guardrails` object means that no policy is active.
- The worker tells the model which guardrails are active. The prompt lists one note for each active guardrail. The note names the policy value, for example `Protect allies: Marcus`.
- The model declares the guardrails it followed in `guardrails_applied`. The worker keeps only the names that the request activated. The response never echoes the input list.
- The worker does not enforce a guardrail in code. Enforcement depends on the model's output. A name that the model omits is not reported.

The Watcher returns the worker's `guardrails_applied` list in its `StandInAction` response.

## The Watcher Routes

The Watcher (`services/the_watcher`) calls the worker for three routes. Each route passes the
worker result through with its `source` field. The Watcher never returns a
canned or template result for a failed worker call.

Configuration:

| Variable | Use |
|---|---|
| `RUNEFOBLE_INFERENCE_URL` | Base URL of the inference worker. Required while `RUNEFOBLE_WATCHER_ENGINE` is `inference_worker`, the default. The Watcher fails at start-up when it is unset. |
| `RUNEFOBLE_WATCHER_ENGINE` | `inference_worker` (default) or `heuristic`. `heuristic` runs the local rule engine for speech and stand-in only. Narration returns 503 under `heuristic`. |
| `RUNEFOBLE_BOARD_STATE_URL` | Base URL of the board state service. Speech reads the session board to send `visible_tokens`. |

| Watcher route | Worker call | Result fields |
|---|---|---|
| `POST /api/v1/watcher/transcribe-and-act` (and `transcribe-and-act`) | `/inference/v1/intent` | `source`. `confidence` is `null` when the worker omits it. |
| `POST /api/v1/watcher/stand-in/act` | `/inference/v1/stand-in-action` | `source`, `guardrails_applied` |
| `POST /api/v1/watcher/narrate` | `/inference/v1/dm-narration` | `source` |

Speech sends the session's tokens as `visible_tokens`. A session with no board sends an empty list.

Each 503 `detail` also carries a `message` string. The stable fields are `error` and `backend`. Clients must not parse `message`.

Error responses from The Watcher:

| Condition | Watcher response |
|---|---|
| Worker returns 200 | Result built from the worker body. |
| Worker returns 503 | HTTP 503 with `detail: {"error": "backend_unavailable", "backend": <worker backend>}`. |
| Worker unreachable | HTTP 503 with `detail: {"error": "backend_unavailable", "backend": "inference_worker"}`. |
| Other worker status | HTTP 502 with `detail: {"error": "inference_worker_error", "status": <code>}`. |
| Board state unreadable, or `RUNEFOBLE_BOARD_STATE_URL` unset on the speech path | HTTP 503 with `detail: {"error": "backend_unavailable", "backend": "board_state"}`. |
| `RUNEFOBLE_INFERENCE_URL` unset while the engine is `inference_worker` | The Watcher does not start. Start-up fails with a message that names the variable. |

Required request fields. A missing field returns HTTP 422:

- Stand-in: `session_id`, `campaign_id`, `scene_context`.
- Narrate: `session_id`, `campaign_id`, `scene_environment`, `tone`.
