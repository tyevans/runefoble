# Inference Worker Response Contract

This page defines the HTTP response contract of the inference worker (`services/inference_worker`). It covers backend failure and response provenance.

## Endpoints

| Method | Path | Response model |
|---|---|---|
| POST | `/inference/v1/intent` | `IntentParseResponse` |
| POST | `/inference/v1/dm-narration` | `DMNarrationResponse` |
| POST | `/inference/v1/stand-in-action` | `StandInActionResponse` |

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

The `backend` value is the active backend name:

- `openai_compatible` or `ollama`: The selected server failed or returned no usable output.
- `unavailable`: `auto` mode found no live server. Start a server, or set the backend to `mock` for tests.

A narration or stand-in response also returns 503 when the model output has no usable JSON. An intent response does not. For intent, the worker uses the regex heuristic and sets `source` to `heuristic`.

## Backend Selection

Set the backend with `RUNEFOBLE_WORKER_BACKEND`:

| Value | Behaviour |
|---|---|
| `auto` | Probes `openai_compatible`, then `ollama`. Returns 503 when neither answers. Never selects `mock`. |
| `openai_compatible` | Calls the configured OpenAI-compatible endpoint. |
| `ollama` | Calls the local Ollama endpoint. |
| `mock` | Returns canned output. Use only for tests and offline checks. |

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

## Watcher Speech Route

The Watcher (`POST /api/v1/watcher/intent`) calls the worker when `RUNEFOBLE_INFERENCE_URL` is set. The Watcher does not return a template reply on failure.

| Condition | Watcher response |
|---|---|
| Worker returns 200 | Intent result built from `action`. |
| Worker returns 503 | HTTP 503 with `detail: {"error": "backend_unavailable", "backend": <worker backend>}`. |
| Worker unreachable | HTTP 503 with `detail: {"error": "backend_unavailable", "backend": "inference_worker"}`. |
| Other worker status | HTTP 502 with `detail: {"error": "inference_worker_error", "status": <code>}`. |

When `RUNEFOBLE_INFERENCE_URL` is not set, The Watcher uses its local rule engine. This is an explicit configuration choice, not a failure fallback.
