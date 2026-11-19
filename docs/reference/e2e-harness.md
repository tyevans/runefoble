# Reference: Playwright BDD E2E Harness

This page describes the end-to-end harness in `e2e/` and `playwright.config.ts`. It states what each part does. For how to write scenarios and step definitions, read [Test User Flows with Playwright BDD](../how-to/test-user-flows-with-playwright-bdd.md).

Governed by ADR-0014 and Hard Invariant 7. The harness performs setup through public frontdoors only. It does not write to a database or to internal service state. Every signed-in persona comes from a real Zitadel sign-in in the browser. The suite never forges a token.

The suite runs against the Kind stack through the Traefik ingress at `http://localhost`. Start the stack before you run it (see [Local Development Setup](../tutorials/01-local-development-setup.md)).

## Layout

```
e2e/
├── features/   # Gherkin .feature files
├── steps/      # Step definitions. common_steps.ts holds the shared steps. sign_in_steps.ts holds the sign-in steps.
└── support/    # Global setup, auth fixtures, Zitadel clients, frontdoor API client, scenario world
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
| `e2e/support/world.ts` | Scenario context: the current user, campaign and session ids, one page per persona, and extra browser contexts. |

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
- Writes: `createCampaign`, `createCharacter`, `assignCampaignRole`, `createCampaignInvite`, `publishCodexEntry`, `createCampaignSession`, `startSession`.

A setup step must throw when the request fails. It must not fall back to a fixed id.

## Playwright Configuration

Source: `playwright.config.ts`.

- Base URL: the `PLAYWRIGHT_BASE_URL` variable. The default is `http://localhost`, the Kind ingress. The gateway API and the App Shell share this origin.
- Zitadel issuer and audience, used by the forged-token negative scenarios: `PLAYWRIGHT_ZITADEL_ISSUER` (default `http://auth.localhost`) and `PLAYWRIGHT_ZITADEL_AUDIENCE` (default `runefoble-api`).
- Defaults live in `e2e/support/env.ts` only. Steps import the values from there.
- Global setup: `e2e/support/global_setup.ts`. It creates the personas (see above).
- Projects: desktop Chromium, Firefox and WebKit.
- Artifacts: a trace on the first retry. A video and a screenshot on failure.
- Web servers: none. The suite does not start the gateway or the App Shell. The Kind stack must already run.

## Make Targets and Scripts

| Command | Runs | Starts browsers |
|---|---|---|
| `make test-bdd` | `pnpm run e2e:typecheck`, then `scripts/check_e2e_unused_steps.py`, then `pnpm exec bddgen` | No |
| `make test-e2e` | `pnpm exec bddgen`, then `pnpm exec playwright test $(ARGS)` with `ZITADEL_ADMIN_PAT` read from the `zitadel-admin` Secret | Yes, all three projects |
| `make test-e2e-ui` | `pnpm exec bddgen`, then `pnpm exec playwright test --ui $(ARGS)` with the same token | Yes |
| `scripts/test_ci_e2e.sh` | Starts the dev servers on `:8000` and `:5173`. It does not start Zitadel or the Kind stack, so it cannot run the real sign-in flow. | Yes |

`make test-e2e` runs this command to read the admin token. The token exists only in the environment of that one process:

```bash
kubectl --context kind-runefoble-local get secret zitadel-admin -o jsonpath='{.data.pat}' | base64 -d
```

Pass Playwright options through `ARGS`. For example:

```bash
make test-e2e ARGS="--project=chromium -g 'Dungeon Master'"
```

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

The asset forge error scenario sends a prompt that asset_forge refuses with `422`. It fakes no reply. The caravan board `503` scenarios still answer the action route with `page.route` in the browser.
