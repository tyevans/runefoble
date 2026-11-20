# Reference: Playwright BDD E2E Harness

This page describes the end-to-end harness in `e2e/` and `playwright.config.ts`. It states what each part does. For how to write scenarios and step definitions, read [Test User Flows with Playwright BDD](../how-to/test-user-flows-with-playwright-bdd.md).

Governed by ADR-0014 and Hard Invariant 7. The harness performs setup through public frontdoors only. It does not write to a database or to internal service state. Every signed-in persona comes from a real Zitadel sign-in in the browser. The suite never forges a token.

The suite runs against the Kind stack through the Traefik ingress at `http://localhost`. Start the stack before you run it (see [Local Development Setup](../tutorials/01-local-development-setup.md)).

## Layout

```
e2e/
├── features/   # Gherkin .feature files
├── steps/      # Step definitions. common_steps.ts holds the shared steps. sign_in_steps.ts holds the sign-in steps.
├── support/    # Global setup, auth fixtures, Zitadel clients, frontdoor API client, scenario world, guards
└── unit/       # Node unit tests for the support modules. They run with node --test. Playwright does not load them.
```

| File | Role |
|---|---|
| `e2e/support/fixtures.ts` | Exports `test`, `Given`, `When` and `Then`. Adds the `auth`, `frontdoorApi` and `world` fixtures. |
| `e2e/support/global_setup.ts` | Creates this run's personas in Zitadel before any test starts. |
| `e2e/support/personas.ts` | The persona keys, the persona registry, and the name resolver. |
| `e2e/support/zitadel_admin.ts` | Zitadel management API client used only by global setup. Reads the admin token from the environment. |
| `e2e/support/zitadel_login.ts` | Drives the Zitadel hosted login page from the App Shell sign-in modal. |
| `e2e/support/app_shell_session.ts` | The App Shell session key and its read-only shape. |
| `e2e/support/auth_fixtures.ts` | The `AuthFixtures` class. `signInAs` signs a persona in through Zitadel. |
| `e2e/support/env.ts` | The only module that reads environment variables. It holds the API base URL, the Zitadel issuer and audience, and the name of the admin token variable. |
| `e2e/support/frontdoor_api.ts` | The `FrontdoorApi` class. Calls public REST routes through the ingress. |
| `e2e/support/campaign_capabilities.ts` | `openAndRecordCapabilities` opens an App Shell route and records the `GET /api/v1/campaigns/{campaign_id}/capabilities` reply. `recordedCapabilities` returns it. Steps compare a role-gated control with the server flag. |
| `e2e/support/world.ts` | Scenario context: the current user, campaign and session ids, one page per persona, and extra browser contexts. `getPage(name)` throws when no step opened a page for that persona. |
| `e2e/support/lobby_session.ts` | Lobby setup state. `rememberLobbySession` and `lobbySessionId` keep the session id with the title that the feature uses. `lobbyRoute` builds the lobby route from the stored ids. `personaToken` returns the bearer token of a persona that setup signed in. |
| `e2e/support/service_faults.ts` | `stopService` and `startService` stop and start an owning service on Kind through the fault make targets (see "Service Faults"). |
| `e2e/support/board_cells.ts` | Board locators. `boardCell` finds the cell with the label `x,y`. `boardToken` finds the token whose title starts with a character name. The battlemap set-up steps (`e2e/steps/battlemap_setup_steps.ts`, TASK-0922) use them. |
| `e2e/support/guards.ts` | Fail-loud guards. `requireValue` throws when a setup value is missing. `assertOk` throws with the status and body of a failed response. `fillRouteTemplate` puts the ids from `world` into a route shape such as `#/campaigns/{campaignId}/sessions/{sessionId}`, and throws when an id is missing. `exactText` builds a whole-text match for `hasText`. |

## Global Setup and Personas

`e2e/support/global_setup.ts` runs once before the tests. It does the following:

1. Reads the admin token from the `ZITADEL_ADMIN_PAT` environment variable. The variable must be set. The setup stops with an error when it is missing.
2. Reads the browser-facing issuer from `GET <base URL>/runtime-config.json`.
3. Creates one verified human user for each persona key through `POST /v2beta/users/human` on the issuer. Each user name carries a random per-run suffix, so runs do not collide.
4. Stores the persona registry, with user ids and generated passwords, in the `RUNEFOBLE_E2E_PERSONAS` environment variable. The registry is never written to disk.

The setup never touches a database. Error messages never contain the admin token.

| Persona key | Name in steps | Zitadel user |
|---|---|---|
| `dm` | `DM`, `Dungeon Master`, `GM`, `master` | Dungeon Master Eldrin |
| `player` | `Player` | Player Adventurer |
| `evelyn` | `Evelyn` | Evelyn Vance |
| `valeros` | `Valeros` | Valeros of Korvosa |
| `sarah` | `Sarah` | Sarah Shadowstep |
| `marcus` | `Marcus` | Marcus Ironhand |

`resolvePersonaKey` matches the name in a step. It ignores case and punctuation. A name that matches no persona throws an error. The suite never falls back to another persona.

Source: `e2e/support/personas.ts`, `e2e/support/global_setup.ts`.

## Authentication Fixture

`AuthFixtures.signInAs(roleOrName, page?)` signs the persona in through Zitadel. The first sign-in of a persona in a worker runs the hosted login in the browser:

1. It clears the cookies of the browser context. Zitadel keeps its own session cookie, and a reused cookie would skip the password page.
2. It opens `#/login`, clears the App Shell storage, and reloads the page.
3. It clicks **Sign In with Zitadel** in the App Shell sign-in modal.
4. It fills the login name and the password on the Zitadel hosted page. It skips an optional second-factor setup prompt.
5. It waits until the App Shell stores its session.
6. It checks that the stored subject equals the persona's Zitadel user id.

Later sign-ins of the same persona in the same worker restore the session that Zitadel issued during that first sign-in. The restore writes the session JSON into the App Shell storage. It runs only while the access token has more than one minute left. A sign-out removes the stored session of that persona, so the next sign-in runs the hosted login again. The sessions stay in worker memory. The suite does not write them to disk.

The access token that `TestUser.token` holds always came from a Zitadel sign-in in the same run. The suite never forges a token.

`TestUser.username` is the Zitadel user name of the persona, for example `evelyn-ab12`. The access token carries the same value as `preferred_username`, so a step can expect it in a member list. The display name (for example Evelyn Vance) is not in the access token.

`AuthFixtures.attemptSignIn(persona, password, page?)` runs the same hosted login with any password. It returns Zitadel's answer. Use it to test refusal, for example with **Password is invalid**.

The token for a negative scenario, such as a token signed by an unknown key, is built in the step. The step signs it with a throwaway RSA key. The gateway refuses it. See `e2e/steps/identity_negative_steps.ts`.

## Frontdoor API Client

`FrontdoorApi` (`e2e/support/frontdoor_api.ts`) sends HTTP requests to public routes such as `POST /api/v1/campaigns`. It sends the bearer token when the caller passes one. The `bearerHeader(token)` helper in the same file builds the `Authorization` header. Every e2e request that carries a token uses it. Its methods include:

- Health and reads: `checkHealth`, `listCampaigns`, `getCampaign`, `listCharacters`, `getCharacter`, `listCampaignMembers`, `getAtlas`, `getCodex`.
- Writes: `createCampaign`, `createCharacter`, `assignCampaignRole`, `createCampaignInvite`, `publishCodexEntry`, `createCampaignSession`, `joinSession`, `startSession`.

A setup step must throw when the request fails. It must not fall back to a fixed id.

## Playwright Configuration

Source: `playwright.config.ts`.

- Base URL: the `PLAYWRIGHT_BASE_URL` variable. The default is `http://localhost`, the Kind ingress. The gateway API and the App Shell share this origin.
- Zitadel issuer and audience, used by the forged-token negative scenarios: `PLAYWRIGHT_ZITADEL_ISSUER` (default `http://auth.localhost`) and `PLAYWRIGHT_ZITADEL_AUDIENCE` (default `runefoble-api`).
- Defaults live in `e2e/support/env.ts` only. Steps import the values from there.
- Global setup: `e2e/support/global_setup.ts`. It creates the personas (see above).
- Projects: desktop Chromium, Firefox and WebKit.
- Clipboard access, so that the invite scenario can read back the copied URL: Chromium gets `clipboard-read` and `clipboard-write`. WebKit gets `clipboard-read`. Firefox has no clipboard permission, so its project sets the `dom.events.testing.asyncClipboard` preference. A clipboard read that the engine refuses fails the step.
- Artifacts: a trace on the first retry. A video and a screenshot on failure.
- Web servers: none. The suite does not start the gateway or the App Shell. The Kind stack must already run.

## Make Targets and Scripts

| Command | Runs | Starts browsers |
|---|---|---|
| `make test-bdd` | `pnpm run e2e:typecheck`, then `node --test e2e/unit/*.test.ts`, then `scripts/check_e2e_unused_steps.py`, then `pnpm exec bddgen` | No |
| `make test-e2e` | `pnpm exec bddgen`, then `pnpm exec playwright test $(ARGS)` with `ZITADEL_ADMIN_PAT` read from the `zitadel-admin` Secret | Yes, all three projects |
| `make test-e2e-ui` | `pnpm exec bddgen`, then `pnpm exec playwright test --ui $(ARGS)` with the same token | Yes |
| `make e2e-lore-down`, `make e2e-lore-up` | `scripts/e2e_service_fault.py campaign_lore down` or `up` (see "Service Faults") | No |
| `make e2e-game-session-down`, `make e2e-game-session-up` | `scripts/e2e_service_fault.py game_session down` or `up` | No |
| `scripts/test_ci_e2e.sh` | Starts the dev servers on `:8000` and `:5173`. It does not start Zitadel or the Kind stack, so it cannot run the real sign-in flow. | Yes |

`make test-e2e` runs this command to read the admin token. The token exists only in the environment of that one process:

```bash
kubectl --context kind-runefoble-local get secret zitadel-admin -o jsonpath='{.data.pat}' | base64 -d
```

Pass Playwright options through `ARGS`. For example:

```bash
make test-e2e ARGS="--project=chromium -g 'Dungeon Master'"
```

## Service Faults

A journey that must see an unavailable owner stops that owner on Kind. It does not fake a reply in the browser (ADR-0014). Source: `scripts/e2e_service_fault.py`, `e2e/support/service_faults.ts`.

| Service | Kind deployment | Make targets | Tag of the restart hook |
|---|---|---|---|
| `campaign_lore` | `campaign-lore` | `e2e-lore-down`, `e2e-lore-up` | `@lore-down` |
| `game_session` | `game-session` | `e2e-game-session-down`, `e2e-game-session-up` | `@game-session-down` |

`down` does these steps:

1. Runs `kubectl --context kind-runefoble-local scale deployment/<name> --replicas=0`.
2. Reads `GET <base URL>/healthz` until `downstream_services.<service>` is `unreachable`.

`up` does these steps:

1. Runs `kubectl --context kind-runefoble-local scale deployment/<name> --replicas=1`.
2. Runs `kubectl --context kind-runefoble-local rollout status deployment/<name>`.
3. Reads `GET <base URL>/healthz` until `downstream_services.<service>` is `operational`.

The base URL is `PLAYWRIGHT_BASE_URL` (default `http://localhost`). Each wait stops after `RUNEFOBLE_E2E_FAULT_TIMEOUT_S` seconds (default `180`). A failed `kubectl` call, a gateway that does not report the service, or a wait that runs out exits with status 1 and a message. The script changes no data. It can scale only the two deployments in the table.

The step that stops a service is `the campaign lore service is stopped` or `the game session service is stopped`. Tag the scenario with the restart tag. The `After` hook for that tag runs the `up` target, also when the scenario fails. The suite runs with one worker, so no other scenario sees the stopped service.

`tests/test_e2e_service_fault.py` tests the script with a fake `kubectl` on `PATH` and a loopback gateway double.

## CI Job

The `e2e-playwright` job in `.github/workflows/ci.yml` runs the suite on each push and pull request to `main`:

1. Starts a `redis:7-alpine` service container.
2. Restores the Playwright browser cache (`~/.cache/ms-playwright`). The cache key uses `pnpm-lock.yaml`.
3. Starts the dev servers with `make dev &`. This job has no Zitadel and no Kind stack. The real sign-in flow of TASK-0525 cannot pass in this job until CI gets a Kind stack with `ZITADEL_ADMIN_PAT`.
4. Polls `http://localhost:8000/healthz` and `http://localhost:5173` for up to 60 seconds.
5. Runs `make test-e2e ARGS="--reporter=github,html"`. The `make` target reads the token with `kubectl`, so this job cannot run it as written.
6. On failure, uploads the Playwright report and the test results as an artifact. The retention period is 14 days.

## Feature Files

The feature files live in `e2e/features/`. They cover the campaign hub, the campaign roster management controls, the campaign rules tab and its homebrew forge, the character sheet, the session lobby and VTT, the lobby role gate and readiness summary, the session chronicle feed, asset forge, the caravan board, the app shell routes, identity negative paths and smoke checks. Read the files for the scenarios. This page does not repeat them.

The asset forge error scenario sends a prompt that asset_forge refuses with `422`. It fakes no reply. The caravan board `503` scenarios stop game_session (see "Service Faults"), so the gateway answers `503` with `Upstream service is unavailable`. The caravan board `403` scenario still answers the action route with `page.route` in the browser, because no frontdoor setup gives a refusal yet. The caravan bearer scenario reads the request headers that leave the browser (TASK-0759).

The smoke step `the top navigation shows the signed-in user` expects `TestUser.username`. The user menu shows the `preferred_username` claim (TASK-0890).
