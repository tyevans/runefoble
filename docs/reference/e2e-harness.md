# Reference: Playwright BDD E2E Harness

This page describes the end-to-end harness in `e2e/` and `playwright.config.ts`. It states what each part does. For how to write scenarios and step definitions, read [Test User Flows with Playwright BDD](../how-to/test-user-flows-with-playwright-bdd.md).

Governed by ADR-0014 and Hard Invariant 7. The harness performs setup through public frontdoors only. It does not write to a database or to internal service state.

## Layout

```
e2e/
├── features/   # Gherkin .feature files
├── steps/      # Step definitions. common_steps.ts holds the shared steps.
└── support/    # Fixtures, auth injection, frontdoor API client, scenario world
```

| File | Role |
|---|---|
| `e2e/support/fixtures.ts` | Exports `test`, `Given`, `When` and `Then`. Adds the `auth`, `frontdoorApi` and `world` fixtures. |
| `e2e/support/auth_fixtures.ts` | Persona table and the `AuthFixtures` class. Injects a session into the browser. |
| `e2e/support/frontdoor_api.ts` | The `FrontdoorApi` class. Calls public REST routes through the gateway. |
| `e2e/support/world.ts` | Scenario context: the current user, campaign and session ids, one page per persona, and extra browser contexts. |

## Authentication Fixture

`AuthFixtures` creates a JWT for a persona. It writes two keys to `localStorage`:

- `rf_auth_session`: the session JSON. It holds the access and refresh tokens, the profile and the roles. The App Shell reads this key.
- `runefoble-user`: the profile JSON.

The fixture writes the keys for later page loads. It also writes them to the current page when one is open. `AuthFixtures.clearAuth` removes both keys and dispatches `rf-auth-changed`.

### Persona Resolution

`resolvePersona` removes every character that is not a letter, then lowercases the name. It checks the rules in this order. The first match wins.

| Name in a step | Resolves to | `user_id` | Roles |
|---|---|---|---|
| `Evelyn` | `evelyn` | `user-dm-evelyn` | `dm`, `player`, `owner` |
| `Valeros` | `valeros` | `user-valeros` | `player` |
| `Sarah` | `sarah` | `user-sarah` | `player` |
| `DM`, `GM`, `master` | `dm` | `user-dm-eldrin` | `dm`, `player` |
| `Spectator` | `spectator` | `user-spectator-zephyr` | `spectator` |
| `Player`, or any other name | `player` | `user-valeros` | `player` |

Source: `PREDEFINED_PERSONAS` and `resolvePersona` in `e2e/support/auth_fixtures.ts`.

## Frontdoor API Client

`FrontdoorApi` (`e2e/support/frontdoor_api.ts`) sends HTTP requests to public routes such as `POST /api/v1/campaigns`. It sends the bearer token when the caller passes one. Its methods include:

- Health and reads: `checkHealth`, `listCampaigns`, `getCampaign`, `listCharacters`, `getCharacter`, `listCampaignMembers`, `getAtlas`, `getCodex`.
- Writes: `createCampaign`, `createCharacter`, `assignCampaignRole`, `createCampaignInvite`, `publishCodexEntry`, `createCampaignSession`, `startSession`.

A setup step must throw when the request fails. It must not fall back to a fixed id.

## Playwright Configuration

Source: `playwright.config.ts`.

- Base URL: the `PLAYWRIGHT_BASE_URL` variable. The default is `http://localhost:5173`.
- Projects: desktop Chromium, Firefox and WebKit.
- Artifacts: a trace on the first retry. A video and a screenshot on failure.
- Web servers: the gateway (`uv run python gateway/api/src/gateway_api/main.py`, ready at `http://localhost:8000/healthz`) and the App Shell (`cd frontend && pnpm run dev`, ready at `http://localhost:5173`). Playwright reuses a server that already runs.
- The gateway starts with `SPICEDB_ENDPOINT` set to `mock` unless the environment sets another value.

## Make Targets and Scripts

| Command | Runs | Starts browsers |
|---|---|---|
| `make test-bdd` | `pnpm run e2e:typecheck`, then `scripts/check_e2e_unused_steps.py`, then `pnpm exec bddgen` | No |
| `make test-e2e` | `pnpm exec bddgen`, then `pnpm exec playwright test $(ARGS)` | Yes, all three projects |
| `make test-e2e-ui` | `pnpm exec bddgen`, then `pnpm exec playwright test --ui $(ARGS)` | Yes |
| `scripts/test_ci_e2e.sh` | Starts the services, waits for `:8000` and `:5173`, then runs `make test-e2e ARGS="--reporter=github,html"` | Yes |

Pass Playwright options through `ARGS`. For example:

```bash
make test-e2e ARGS="--project=chromium -g 'Dungeon Master'"
```

## CI Job

The `e2e-playwright` job in `.github/workflows/ci.yml` runs the suite on each push and pull request to `main`:

1. Starts a `redis:7-alpine` service container.
2. Restores the Playwright browser cache (`~/.cache/ms-playwright`). The cache key uses `pnpm-lock.yaml`.
3. Starts the services with `make dev &`.
4. Polls `http://localhost:8000/healthz` and `http://localhost:5173` for up to 60 seconds.
5. Runs `make test-e2e ARGS="--reporter=github,html"`.
6. On failure, uploads the Playwright report and the test results as an artifact. The retention period is 14 days.

## Feature Files

The feature files live in `e2e/features/`. They cover the campaign hub, the character sheet, the session lobby and VTT, the session chronicle feed, asset forge, the caravan board, the app shell routes, identity negative paths and smoke checks. Read the files for the scenarios. This page does not repeat them.
