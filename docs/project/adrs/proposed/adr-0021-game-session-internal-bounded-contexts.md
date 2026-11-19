# ADR-0021: Bounded Context Packages Inside game_session

## Status
Proposed

## Context
`services/game_session` holds about 15,700 lines of Python in a flat layout (`services/game_session/src/game_session/`). The architecture overview describes the service as "active sessions, turns, dice, and spectator view". The code holds more domains than that (TASK-0753, audit `refactor-r1/game-session.md` F4):

- Campaign lifecycle, invites, and membership (`campaign/`). ADR-0015 (a) gives this domain to `game_session`.
- User profile (`profile/`).
- Session lobby, turns, combat, reactions, director, and auto-pilot (`aggregate/`, `models/`, `reactions/`, `routers/session.py`, `routers/combat.py`).
- Campfire rests, the party stronghold, tavern games, minigame tables, and merchants (`routers/campfire.py`, `stronghold.py`, `minigames.py`, `minigame_tables/`, `merchants.py`). PRD-0014 governs these.
- Settlement havens, establishments, NPC workers, haggling, and the bulletin board (`settlement/`, `routers/settlements.py`). PRD-0024 governs these.
- West Marches shared worlds, caravans, caravan contracts, and mercenary bounties (`west_marches.py`, `caravan/`, `contracts/`, `routers/caravan_contracts/`, `routers/bounties.py`). PRD-0018 governs these.
- Child indexes for list queries (`child_index.py`, `queries/`).

The modules have no package boundary. The import graph shows these problems:

1. **Shared code lives in a domain package.** Route identity (`get_principal`, `CallerId`) is in `settlement/auth/tokens.py`. Routers of every domain import it, for example `campaign/routes.py:42`, `profile/routes.py:16`, `routers/combat.py`, `routers/bounties.py:30`, and `routers/west_marches.py:15`.
2. **One module builds the repositories of all domains.** `dependencies.py:46-69` builds 13 repositories at import time. Every router imports it. TASK-0755 removes this.
3. **Domains import each other's aggregates.** `campaign/session_bootstrap.py:12`, `campaign/service_campaigns.py:12`, and `campaign/routes.py:13` import `GameSessionAggregate`. `routers/campfire.py:13-14` reads the session repository and the stronghold repository.
4. **Re-export shims exist.** `models.py` copies the names of the `models/` package. `models/settlement.py` re-exports settlement names into the play models (`models/__init__.py:39-47`). DoR 9 does not allow shims.
5. **Two modules mix domains.** `events.py` holds the stream names of all domains and the session event mapping. `child_index.py:21-29` lists the index kinds of three domains in one enum.

The audit proposes four packages: `campaign`, `play` (session, combat, tavern, minigames, merchants), `settlement`, and `world` (West Marches, caravans, bounties, stronghold). It also asks if `settlement` must become a separate service.

Options considered:

- **Option A. Keep the flat layout.** Fix only the architecture overview. The cross-domain imports stay and grow.
- **Option B. Four packages, as the audit proposes.** `play` gets about 5,700 lines from two PRDs. The stronghold goes to `world`, but `campfire` in `play` reads it, and its routes are under `/api/v1/campaigns/{campaign_id}`. PRD-0014 is split across two packages.
- **Option C. Five domain packages and one shared kernel, in one deployable service.** Each PRD maps to one package.
- **Option D. Separate deployable services now.** Each new service needs a Helm deployment, an OpenAPI registration (Hard Invariant 5), gateway route ownership, and a service credential (ADR-0015 (e)). No scaling or release need exists.

## Decision
We choose **Option C**.

### D1. Package list
`game_session` has five domain packages and one shared kernel. Each is a Python subpackage of `game_session`.

| Package | Domain | Governing records | Size today (lines) |
|---|---|---|---|
| `game_session.campaign` | Campaign lifecycle, invites, membership, campaign sessions list, user profile | ADR-0015 (a) | about 1,700 |
| `game_session.play` | Session lobby, presence, turns, initiative, combat, reactions, director, auto-pilot, chronicle, spectator view, audience weather | PRD-0001, PRD-0002, PRD-0005 | about 3,200 |
| `game_session.downtime` | Campfire rests, party stronghold, tavern games, minigame tables, merchants | PRD-0014 | about 2,800 |
| `game_session.settlement` | Settlement havens, establishments, NPC workers, haggling, bulletin board | PRD-0024 | about 4,700 |
| `game_session.world` | West Marches shared worlds, outposts, discoveries, caravans, caravan contracts, mercenary bounties | PRD-0018 | about 2,600 |
| `game_session.shared` | Route identity, permission helpers used by two or more packages, child index mechanism, stream names | ADR-0001, ADR-0006, ADR-0015 (c) | about 300 |

The composition root is outside the packages: `main.py` and the container of D6.

### D2. Owner of each current module
Paths are relative to `services/game_session/src/game_session/`.

| Current module | Owner |
|---|---|
| `campaign/` | `campaign` |
| `profile/` | `campaign` |
| `aggregate/`, `models/` (without `models/settlement.py`), `reactions/`, `rules.py`, `encounter_settings.py` | `play` |
| `auth/session_access.py`, `routers/session_auth.py` | `play` |
| `chronicle.py`, `spectator.py`, `audience_weather.py`, `character_client.py` | `play` |
| `routers/session.py`, `combat.py`, `encounters.py`, `director.py`, `reactions.py`, `autopilot.py`, `chronicle.py` | `play` |
| Session event mapping and `SessionEventPublisher` in `events.py` | `play` |
| `routers/campfire.py`, `stronghold.py`, `routers/stronghold.py` | `downtime` |
| `minigames.py`, `minigame_rules.py`, `minigame_tables/`, `merchants.py`, `merchants_service.py`, `voice_client.py` | `downtime` |
| `routers/tavern.py`, `routers/minigames_ws.py` | `downtime` |
| `settlement/` (without `settlement/auth/tokens.py`), `routers/settlements.py` | `settlement` |
| `west_marches.py`, `west_marches_models.py`, `caravan/`, `contracts/` | `world` |
| `routers/west_marches.py`, `routers/caravan_trade.py`, `routers/caravan_contracts/`, `routers/bounties.py` | `world` |
| `settlement/auth/tokens.py` | `shared` (route identity) |
| `check_establishment_play_permission` in `settlement/auth/permissions.py:81` | `shared` (`downtime` and `settlement` call it) |
| `child_index.py` (aggregate and stream id), `queries/child_index.py` | `shared` |
| Stream name constants in `events.py` | `shared` |
| `dependencies.py` | Replaced by the container of D6 (TASK-0755) |
| `models.py`, `models/settlement.py` | Deleted. They are shims (DoR 9). |

Rules for code that the table does not name:
- A new module goes to the package whose aggregate it changes or reads.
- A SpiceDB permission helper stays in the package that calls it. When a second package calls it, it moves to `shared`.
- Each child index kind moves to the package that owns the parent object. `shared` keeps the mechanism and accepts the kind as a string. The kind values do not change, so the index stream ids (`child_index.py:32-34`) do not change.

### D3. No package becomes a deployable service now
`game_session` stays one deployment, one OpenAPI document, one UI package (`@runefoble/game-session-ui`), and one `/ui/manifest`.

`settlement` is the first candidate for a separate service. Its haggling and worker graph have their own lifecycle. A new ADR must decide the split. That ADR must show one of these needs: independent scaling, an independent release cadence, or a separate owner team. When D4 is in force, a split replaces in-process adapters with HTTP adapters on the shared `ServiceClient`. The domain code does not change.

### D4. Import rule between packages: ports only
1. A domain package imports only its own modules, `game_session.shared`, the `libs/` packages, and third-party packages.
2. A domain package never imports another domain package.
3. When a package needs data or an action from another package, it declares a port. A port is a `typing.Protocol` in `<package>/ports.py` of the consumer package. Port methods take and return plain values or Pydantic models of the consumer package. They never return an aggregate of another package.
4. The composition root (`main.py` and the container) is the only code that imports two or more domain packages. It builds the adapter for each port and injects it.
5. `game_session.shared` imports no domain package.
6. Domain events and their payloads in `libs/runefoble_events` are published language. Any package can consume them from Redis Streams.
7. A permission check on a SpiceDB object of another domain is not an import. A package calls `runefoble_auth` with the object type and id from `runefoble.zed`.
8. Ports to other services (Character Sheet, Voice Agent, The Watcher) follow the same rule. The consumer package declares the port. The adapter uses the shared `ServiceClient` (ADR-0015 (b)) and lives in `game_session/adapters/`.
9. A lint contract enforces rules 1, 2, and 5. `make lint` runs it.

The current cross-package edges become these ports:

| Edge today | Port | Declared in | Implemented from |
|---|---|---|---|
| `campaign` creates a session (`campaign/session_bootstrap.py:12-28`) | `SessionOpener` | `campaign/ports.py` | `play` |
| `downtime` checks session participation and reads the session campaign and participants (`routers/campfire.py:75-90`, `routers/tavern.py`) | `SessionRoster` | `downtime/ports.py` | `play` |
| All routers import identity from `settlement/auth/tokens.py` | None. Identity moves to `shared`. | | |
| `models/settlement.py` re-exports settlement models into `play` | None. The shim is deleted. | | |
| `play` calls Character Sheet and The Watcher (`character_client.py`, `routers/autopilot.py:25`) | `CharacterSheetPort`, `WatcherPort` (TASK-0754) | `play/ports.py` | `adapters/` |
| `downtime` calls Voice Agent (`voice_client.py`) | `VoiceAgentPort` (TASK-0754) | `downtime/ports.py` | `adapters/` |

### D5. Routes do not change
- OpenAPI paths, HTTP methods, request and response schemas, and WebSocket routes stay the same during the migration.
- Each domain package exposes one `router` (`APIRouter`). `main.py` includes the five routers.
- The `prefix="/api/v1"` arguments at `main.py:107` and `main.py:111` move into the package routers. The full paths stay the same.
- Event types, stream names, and SpiceDB definitions do not change. The gateway route table does not change.

### D6. Composition root and app container
TASK-0755 implements this decision for `game_session`. TASK-0859 applies the same pattern to `asset_forge`, `campaign_analytics`, `campaign_lore`, and `voice_agent`.

1. Each service has one composition root module, `<service>/container.py`. It defines one frozen container class, for example `GameSessionContainer`.
2. A function `build_container(settings)` builds the container. It reads the settings once. It raises at start-up when a required setting is missing, for example the event store in a deployed environment (ADR-0015 (f)) or the Watcher URL (now `dependencies.py:38-44`).
3. The FastAPI lifespan calls `build_container` and stores the result on `app.state.container`. Lifespan shutdown closes what the container opened.
4. Routers get dependencies through FastAPI `Depends` providers that read `request.app.state.container` or `websocket.app.state.container`. Stream consumers receive the container when the lifespan starts them.
5. In `game_session`, each domain package has `<package>/repositories.py`. It defines one frozen dataclass of the package repositories and one function `build_<package>_repositories(...)`. The pattern is `CampaignRepositories` and `build_campaign_repositories()` in `campaign/repositories.py:22-37`. The container holds one dataclass for each package and the child index repository of `shared`.
6. No module builds a service object, a repository, or a client at import time. No module has `get_`/`set_` globals for test injection, for example `campaign/repositories.py:40-52` and `set_event_bus` at `dependencies.py:124-126`.
7. `main.py` exposes `create_app(build=build_container)`. Tests call `create_app` with a builder that returns a test container. The production builder never selects the in-memory event store (ADR-0015 (f)). Tests keep their frontdoor assertions (Hard Invariant 7).
8. TASK-0755 groups the repositories by the D1 packages, also before the code moves. The moves of D7 then do not change the container shape.

### D7. Migration order
Each step is one backlog task. Each step keeps all blackbox suites green and the routes of D5 unchanged.

1. **Shared kernel.** Create `game_session/shared/`. Move route identity, the shared permission helper, the child index mechanism, and the stream names. Delete `models.py` and `models/settlement.py`. Update all call sites and tests directly (DoR 9).
2. **App container (TASK-0755).** It also needs TASK-0567. It applies D6.
3. **Service ports (TASK-0754).** It declares the ports of D4 in `play/ports.py` and `downtime/ports.py`, with adapters in `adapters/`. It injects them through the container. If it lands before step 2, it injects them through `dependencies.py`, and step 2 moves them.
4. **Move packages, one task for each package:** `world`, then `settlement`, then `downtime` (with `SessionRoster`), then `campaign` (with `SessionOpener`), then `play`. Each move updates the imports of the tests and docs in the same commit.
5. **Enforce.** Turn on the lint contract of D4 rule 9. Update the `game_session` rows in AGENTS.md and `docs/reference/architecture-overview.md`, and the paths in `docs/reference/game-session-child-indexes.md`.
6. **Other services (TASK-0859).** It can start after step 2. It does not depend on steps 3 to 5.

## Consequences
- **Positive**:
  - Each PRD maps to one package. A reader finds the code of a feature in one place.
  - The import graph has no cycles between domains. A change in one package cannot break the imports of another package.
  - A later split of `settlement` into a service changes adapters only.
  - Start-up fails fast and in one place. Tests inject a container, not module globals.
- **Negative**:
  - The moves change import paths across the service and about 170 test files that import `game_session`. Parallel work on `game_session` conflicts during each move. Each move is a short task that the orchestrator schedules alone.
  - Ports add code. `SessionOpener` and `SessionRoster` are small, but each needs an adapter and a container entry.
  - The lint contract needs a tool or a configuration that the repository does not have now.
- **Neutral**:
  - Two merchant models exist: `MerchantAggregate` (`merchants.py`, PRD-0014) in `downtime` and `NegotiationAggregate` (`settlement/haggling/`, PRD-0024) in `settlement`. This ADR does not merge them.
  - The UI package stays one package for the service (ADR-0013).

## References
- [`adr-0007-domain-driven-design-architecture.md`](../accepted/adr-0007-domain-driven-design-architecture.md): layering inside each package.
- [`adr-0011-eventsource-py-core-event-sourcing.md`](../accepted/adr-0011-eventsource-py-core-event-sourcing.md): repositories and aggregates.
- [`adr-0013-microfrontend-architecture-and-service-component-vendoring.md`](../accepted/adr-0013-microfrontend-architecture-and-service-component-vendoring.md): one UI package for each service.
- [`adr-0015-audit-remediation-decisions.md`](../accepted/adr-0015-audit-remediation-decisions.md): (a) campaign ownership, (b) shared service client, (f) fail fast.
- [`adr-0017-file-length-invariant.md`](../accepted/adr-0017-file-length-invariant.md): file length limit.
- [`docs/reference/architecture-overview.md`](../../../reference/architecture-overview.md)
- [`docs/reference/game-session-child-indexes.md`](../../../reference/game-session-child-indexes.md)
- TASK-0753 (this spike), TASK-0754, TASK-0755, TASK-0859, TASK-0491, TASK-0550.
