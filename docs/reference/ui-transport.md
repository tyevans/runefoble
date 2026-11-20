# Reference: UI Transport (`@runefoble/ui-core`)

The shared HTTP client for every microfrontend and the App Shell. It lives in `libs/runefoble_ui/src/http.ts` (TASK-0825, TASK-0758). It is the browser counterpart of the Python [service client](service-client.md) that the gateways use.

Do not write a local `fetch` call, error class or error body reader in a UI package. Call `request` or one of its POST helpers.

## Functions

| Export | Behaviour |
|---|---|
| `request<T>(path, spec?, opts?)` | Sends `path` under `opts.apiBase` with the headers of `opts.auth` and `opts.headers`. Resolves with the parsed JSON body. An empty success body resolves with `undefined`. |
| `postJson<T>(path, body, opts?)` | `request` with `POST` and `JSON.stringify(body)`. |
| `postForm<T>(path, form, opts?)` | `request` with `POST` and a `FormData` body (for example an asset upload). |
| `apiUrl(apiBase, path)` | Joins the API base and the path. A trailing slash on the base is removed. |
| `requestFailureMessage(err)` | The user-facing text of a failure: `HttpError.detail`, the unreadable-body text of `UnreadableResponseError`, else `Network error: <reason>`. |
| `actionFailureMessage(err, action)` | The user-facing text of a failed action (TASK-0759). See [Status-Specific Text](#status-specific-text). |
| `errorDetailFromBody(body)` | The FastAPI `detail` string, or the joined `detail[].msg` values of a `422`. |
| `bearerHeaders(token)` | `{ Authorization: 'Bearer <token>' }` for a token, else `{}`. |

## `RequestSpec`

`RequestSpec` is `RequestInit` without `headers`, and with `body` limited to a JSON string or a `FormData`.

| Body | `Content-Type` that `request` sends |
|---|---|
| A string | `application/json` |
| A `FormData` | None. The browser sets `multipart/form-data` with the boundary. |
| None | None |

## `RequestOptions`

| Field | Meaning |
|---|---|
| `apiBase` | API base URL put in front of the path, for example `https://gateway.example`. Empty or absent means the page origin. |
| `auth` | An `AuthSource`: an object with `authHeaders(): Promise<Record<string, string>>`. `AuthConsumerController` is one. `request` reads it once for each call. With no token it gives `{}`, so no `Authorization` header is sent. |
| `headers` | Extra headers. A header here wins over an auth header with the same name. |
| `fetchImpl` | Transport override. The default reads the global `fetch` at call time, so a Storybook stand-in installed later still applies. |

## Errors

| Case | Result |
|---|---|
| A non-2xx response | Rejects with `HttpError { status, detail }`. |
| `detail` of the error | The FastAPI `detail` (a string, or the joined `msg` values). Else the `message` of an engine-unavailable body (`{"error", "message"}`). Else `Request failed with status <code>`. |
| A 2xx response whose body is not JSON | Rejects with `UnreadableResponseError { status }`. |
| A network failure | Rejects with the fetch error (a `TypeError`). It is not an `HttpError`. |

Nothing resolves on failure. No call returns substitute data (ADR-0015 b).

## Status-Specific Text

A caller renders `HttpError.detail`, or calls `actionFailureMessage(err, action)`. `action` names the action, for example `caravan action`.

| Status | Text of `actionFailureMessage` |
|---|---|
| `401` | `Sign in to continue with this <action>.` |
| `403` | `Your account is not authorized for this <action>.` |
| `503` | `Service unavailable: <detail>`. With no server detail: `Service unavailable. Try again later.` |
| Other codes | The detail. |
| A network failure | `Network error: <reason>`. |

Some packages have their own status-specific text:

| Package | Function | Text |
|---|---|---|
| `@runefoble/game-session-ui` | `caravan/caravan_api.ts` | `actionFailureMessage(err, 'caravan action')`. The board puts `Accept failed: `, `Dispatch failed: ` or `Fulfilment failed: ` in front. |
| `@runefoble/rules-compendium-ui` | `<runefoble-encounter-builder>` | `actionFailureMessage(err, 'encounter balance request')` in a `role="alert"` box. |
| `@runefoble/asset-forge-ui` | `forgeFailureMessage(err)` | `401`: a sign-in message. `403`: a permission message. Other codes: the detail. |
| `@runefoble/board-state-ui` | `<runefoble-map-dropzone>` | `Upload failed: <detail>` for every status. |

## Callers

| Package | Module | Calls |
|---|---|---|
| `@runefoble/asset-forge-ui` | `forge-api.ts` | Every forge route, and `POST /api/v1/boards/{session_id}/tokens`. Each function takes `(input, opts)`. The elements pass `{ apiBase: this.apiBaseUrl, auth: this.auth }`. |
| `@runefoble/board-state-ui` | `board-api.ts` | `POST /api/v1/boards/{id}/traps`. |
| `@runefoble/board-state-ui` | `physics_3d/physics_bridge.ts` | `POST /api/v1/boards/{id}/physics/simulate-throw` and `/knockback`. The API base is the `apiBaseUrl` of the host element (`<runefoble-board>`, `<runefoble-tabletop-3d>`). |
| `@runefoble/board-state-ui` | `runefoble-map-dropzone.ts` | `POST /api/v1/assets/upload` with `postForm`. The API base is its `apiBaseUrl` property. `<runefoble-map-uploader>` passes its own `apiBaseUrl` down. |
| `@runefoble/game-session-ui` | `caravan/caravan_api.ts` | `POST /shared-worlds/{id}/caravans/contracts/{contract_id}/accept`, `/dispatch` and `/fulfill` under the board `api-base` (default `/api/v1`). One POST function serves the three routes. The board passes its `AuthConsumerController` as `auth`. No call sends `x-user-id`. |
| `@runefoble/rules-compendium-ui` | `runefoble-encounter-builder.ts` | `POST /api/v1/compendium/encounters/balance` under `apiBaseUrl`, with `{ apiBase, auth }`. An empty `apiBaseUrl` shows `The compendium service address is not set.` and sends nothing. |
| App Shell (`frontend/`) | `services/shell-request.ts` | `requestData(path, spec, headers)` sends through `request` with `shellAuth` (from `auth/transport.ts`) and returns a `DataResult`. `AppDataService.request` and `fetchPartyVitals` use it. `HttpError` keeps its status and detail. `UnreadableResponseError` gives the unreadable-response text. A fetch `TypeError` gives status `0` and the network text. |

Protected asset reads (`<img>` bytes) use `fetchAssetObjectUrl` instead. See [Browser asset reads](browser-asset-reads.md).

## Test Support

Test the transport against a real HTTP server, not a replaced `fetch`.

| Module | Use |
|---|---|
| `@runefoble/ui-core/testing/loopback-upstream` | `startLoopbackUpstream()` starts a server on `127.0.0.1` with a free port. It records each request (method, path, headers, body) and answers with the reply that `reply(status, body)` sets. It answers CORS preflights. Node only. |
| `@runefoble/ui-core/testing/loopback-commands` | `loopbackUpstreamCommands`: Vitest browser commands (`upstreamUrl`, `upstreamReply`, `upstreamReset`, `upstreamRequests`) over one shared loopback upstream. Pass them to `domTestConfig(dir, { commands: loopbackUpstreamCommands })`. |

Examples:
- `libs/runefoble_ui/test/request-loopback.test.ts`: the transport itself.
- `services/asset_forge/ui/test-dom/forge-transport.test.ts`: the forge elements render the `403` and `503` text, and the upstream sees the URL and the bearer.
- `services/board_state/ui/test-dom/map-upload-transport.test.ts`: the multipart upload and its `403` and `503` text.
- `services/game_session/ui/test-dom/caravan-board-transport.test.ts`: the caravan board sends the bearer, and shows distinct `403` and `503` text.
- `services/rules_compendium/ui/test-dom/encounter-builder-transport.test.ts`: the encounter balance request sends the bearer, and shows the `403`, `503` and `422` text.
